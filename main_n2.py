import pickle
import argparse
import collections
from pathlib import Path
from ortools.sat.python import cp_model


def main():
	args = _args()
	slices, jobs = read_input(args.input_path)
	decomposed_job_shop(slices, jobs, args.output_path, args.group_size, args.time_out)


def decomposed_job_shop(slices, jobs, output_file_path, group_size, time_out):

	# sort jobs accoring to their CP value
	job_rating = []
	for job_id, job in enumerate(jobs):

		total_resource = 0 # n_slice * time
		for op_id, op in enumerate(job[1]):
			total_resource += op[0] * op[1]

		weight = job[0]
		job_rating.append((job_id, weight / total_resource))

	job_rating = sorted(job_rating, key = lambda x : x[1], reverse = True)
	ordered_jobs = []
	order_id_to_id = []

	for job_id, rating in job_rating:
		ordered_jobs.append(jobs[job_id])
		order_id_to_id.append(job_id)

	print(f"order_id_to_id: {order_id_to_id}")
	# find optimal solution to GROUP_SIZE jobs
	operation_info = {} # key = (job_id, op_id), value = (start_time, [machine_id...])
	machine_avalible_time = [0] * slices

	GROUP_SIZE = group_size
	n_selected_job = 0
	while n_selected_job < len(ordered_jobs):
		selected_jobs = ordered_jobs[n_selected_job : min(n_selected_job + GROUP_SIZE, len(ordered_jobs))]
		print(f"selected jobs {selected_jobs}")
		# schedule these jobs
		solver, status, ops_start, presences = job_shop(slices, selected_jobs, machine_avalible_time, time_out)  # solve problem

		# job_id here is not the same as original job's counterpart
		for job_id, job in enumerate(selected_jobs):
			for op_id, op in enumerate(job[1]):
				required_machine = []
				for m_id in range(slices):
					if solver.Value(presences[(job_id, op_id, m_id)]):
						required_machine.append(m_id+1)
						start_time = solver.Value(ops_start[(job_id, op_id)])
						if (start_time + op[1]) >= machine_avalible_time[m_id]:
							machine_avalible_time[m_id] = (start_time + op[1])


				info = (solver.Value(ops_start[(job_id, op_id)]), required_machine)
				print(f"job/operation pair {order_id_to_id[n_selected_job+job_id]}.{op_id}")
				operation_info[(order_id_to_id[n_selected_job+job_id], op_id)] = info # add info using original ids
		print(f"operation_info {operation_info}")
		n_selected_job += GROUP_SIZE

	# output
	with open(output_file_path, 'w') as f:
		for job_id, job in enumerate(jobs):
			for op_id, op in enumerate(job[1]):
				print(operation_info[(job_id, op_id)][0], end = ' ')
				f.write(str(operation_info[(job_id, op_id)][0]) + ' ')

				for m_id in operation_info[(job_id, op_id)][1]:
					print(m_id, end = ' ')
					f.write(str(m_id) + ' ')

				print()
				f.write('\n')

def job_shop(slices, jobs, machine_avalible_time, time_out):
	model = cp_model.CpModel()

	min_start = min(machine_avalible_time)
	max_start = max(machine_avalible_time)
	horizon = max(machine_avalible_time) + sum([op[1] for job in jobs for op in job[1]])  # Maximun time

	intervals_per_resources = collections.defaultdict(list)
	ops_start = {}  # key: (job_id, op_id), value: NewIntVar(start time of op of job)
	jobs_end = []  # value: NewIntVar(makespan of job_id)
	presences = {}  # key: (job_id, op_id, machine_id), value: selected machine of op of job
	ops_min_slice = {}

	temp_id = 0
	for job_id, job in enumerate(jobs):
		ops_end = []  # end time of all operations in this job
		for op_id, op in enumerate(job[1]):
			machine, duration = op[0], op[1]  # machines and duration the op need

			# Start time and end time of this operation
			name_suffix = ' job %d op %d' % (job_id, op_id)
			start = model.NewIntVar(min_start, horizon, 'start' + name_suffix)
			end = model.NewIntVar(min_start, horizon, 'end' + name_suffix)
			min_slice_index = model.NewIntVar(0, slices, 'max slice' + name_suffix)

			ops_start[(job_id, op_id)] = start

			l_presences = []  # assigned machine (one hot)
			l_indexs = []
			for m_id in range(slices):
				m_suffix = ' job %d op %d m %d' % (job_id, op_id, m_id)
				l_presence = model.NewBoolVar('presence' + m_suffix)  # Assigned to or not
				l_start = model.NewIntVar(machine_avalible_time[m_id], horizon, 'start' + m_suffix)
				l_end = model.NewIntVar(machine_avalible_time[m_id], horizon, 'end' + m_suffix)
				l_interval = model.NewOptionalIntervalVar(l_start, duration, l_end, l_presence, 'interval' + m_suffix)
				l_index = model.NewIntVar(0, slices, 'slice index' + m_suffix)

				l_presences.append(l_presence)
				l_indexs.append(l_index)

				model.Add(start == l_start).OnlyEnforceIf(l_presence)  # Set op start time constraint
				model.Add(end == l_end).OnlyEnforceIf(l_presence)  # Set op end time constraint
				model.Add(l_index == m_id).OnlyEnforceIf(l_presence)
				model.Add(l_index == slices).OnlyEnforceIf(l_presence.Not())

				intervals_per_resources[m_id].append(l_interval)

				presences[(job_id, op_id, m_id)] = l_presence  # Whether op_id of job_id assigned to machine_id

			# set min index of slice selected by operation
			model.AddMinEquality(min_slice_index, l_indexs)
			ops_min_slice[(job_id, op_id)] = min_slice_index

			# Assign operations to enough slices
			model.Add(sum(l_presences) == machine)
			ops_end.append(end)

			temp_id += 1

		# Set precedence constraints
		for op_id, op in enumerate(job[1]):
			for depend in op[2]:
				model.Add(ops_start[(job_id, op_id)] >= ops_end[depend - 1])
		# Link job end time with max(ops end time)
		job_end = model.NewIntVar(min_start, horizon, 'end of job %i' % job_id)
		model.AddMaxEquality(job_end, ops_end)
		jobs_end.append(job_end)

	# break slice interchange permutation
	start_time_bool = []
	for job_id1 in range(len(jobs)):
		for op_id1 in range(len(jobs[job_id1][1])):
			temp_ = []
			for temp_id in range(op_id1 + 1, len(jobs[job_id1][1])):
				cond = model.NewBoolVar('same start j %d o %i j %d o %d' % (job_id1, op_id1, job_id1, temp_id))
				model.Add(ops_start[(job_id1, op_id1)] == ops_start[(job_id1, temp_id)]).OnlyEnforceIf(cond)
				model.Add(ops_start[(job_id1, op_id1)] != ops_start[(job_id1, temp_id)]).OnlyEnforceIf(cond.Not())
				temp_.append(cond)

			for job_id2 in range(job_id1 + 1, len(jobs)):
				for op_id2 in range(len(jobs[job_id2][1])):
					cond = model.NewBoolVar('same start j %d o %i j %d o %d' % (job_id1, op_id1, job_id2, op_id2))
					model.Add(ops_start[(job_id1, op_id1)] == ops_start[(job_id2, op_id2)]).OnlyEnforceIf(cond)
					model.Add(ops_start[(job_id1, op_id1)] != ops_start[(job_id2, op_id2)]).OnlyEnforceIf(cond.Not())
					temp_.append(cond)
			start_time_bool.append(temp_)



	temp = 0
	for job_id1 in range(len(jobs)):
		for op_id1 in range(len(jobs[job_id1][1])):
			temp1 = 0
			for temp_id in range(op_id1 + 1, len(jobs[job_id1][1])):
				model.Add(ops_min_slice[(job_id1, op_id1)] < ops_min_slice[(job_id1, temp_id)]).OnlyEnforceIf(start_time_bool[temp][temp1])
				temp1 += 1

			for job_id2 in range(job_id1 + 1, len(jobs)):
				for op_id2 in range(len(jobs[job_id2][1])):
					model.Add(ops_min_slice[(job_id1, op_id1)] < ops_min_slice[(job_id2, op_id2)]).OnlyEnforceIf(start_time_bool[temp][temp1])
					temp1 += 1
			temp += 1

	# Machine constraints
	for m_id in range(slices):
		intervals = intervals_per_resources[m_id]
		if len(intervals) > 1:
			model.AddNoOverlap(intervals)

	# Set objective function  (scale float to fit in integer)
	weight = [int(job[0] * 10000) for job in jobs]  # w_i
	makespan = model.NewIntVar(min_start, horizon, 'makespan')  # max c_i
	model.AddMaxEquality(makespan, jobs_end)  # max c_i = max (end time of all jobs)
	weighted_sum = cp_model.LinearExpr.ScalProd(jobs_end, weight)  # \sum_i w_i * c_i
	model.Minimize(cp_model.LinearExpr.Sum([cp_model.LinearExpr.Term(makespan, 10000), weighted_sum]))

	# Solve
	solver = cp_model.CpSolver()
	solver.parameters.num_search_workers = 8
	solver.parameters.max_time_in_seconds = time_out
	status = solver.Solve(model)


	print('Solve status: %s' % solver.StatusName(status))
	print('Optimal objective value: %i' % solver.ObjectiveValue())
	print('Statistics')
	print('  - conflicts : %i' % solver.NumConflicts())
	print('  - branches  : %i' % solver.NumBranches())
	print('  - wall time : %f s' % solver.WallTime())

	return solver, status, ops_start, presences

def read_input(file_path):
	jobs = []
	with open(file_path, 'r') as f:
		slices = int(f.readline().strip())
		job_num = int(f.readline().strip())

		for job_id in range(job_num):
			job = []

			op_num = int(f.readline().strip())
			job_weight = float(f.readline().strip())

			for op_id in range(op_num):
				temp = [int(d) for d in f.readline().strip().split()]

				job.append([temp[0], temp[1], temp[3:]])

			jobs.append([job_weight, job])

	return slices, jobs

def write_output(file_path, jobs, solver, status, ops_start):
	with open(file_path, 'w') as f:
		for job_id, job in enumerate(jobs):
			for op_id, op in enumerate(job[1]):
				start_value = solver.Value(ops_start[(job_id, op_id)])
				print(start_value, end = ' ')
				f.write(str(start_value) + ' ')

				for m_id in range(slices):
					if solver.Value(presences[(job_id, op_id, m_id)]):
						print(m_id + 1, end = ' ')
						f.write(str(m_id + 1) + ' ')

				print()
				f.write('\n')


# 	print('Solve status: %s' % solver.StatusName(status))
# 	print('Optimal objective value: %i' % solver.ObjectiveValue())
# 	print('Statistics')
# 	print('  - conflicts : %i' % solver.NumConflicts())
# 	print('  - branches  : %i' % solver.NumBranches())
# 	print('  - wall time : %f s' % solver.WallTime())

def _args():
	parser = argparse.ArgumentParser()
	parser.add_argument('input_path', type=Path, help='input data path')
	parser.add_argument('output_path', type=Path, help='output data path')
	parser.add_argument('-g', '--group_size', type=int, default=8, help="decomposition group size")
	parser.add_argument('-t', '--time_out', type=float, default=960.0, help="solver timeout")
	args = parser.parse_args()
	return args

if __name__ == '__main__':
	main()
