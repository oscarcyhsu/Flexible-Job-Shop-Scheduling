import pickle
import argparse
import collections
from pathlib import Path
from ortools.sat.python import cp_model

class VarArraySolutionPrinterWithLimit(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, limit):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.__solution_limit = limit

    def on_solution_callback(self):
        if self.__solution_count >= self.__solution_limit:
            print('Stop search after %i solutions' % self.__solution_limit)
            self.StopSearch()

    def solution_count(self):
        return self.__solution_count

def main():
	args = _args()

	slices, jobs = read_input(args.input_path)
	solver, status, ops_start = job_shop(slices, jobs, args.output_path)  # solve problem
	# write_output(args.output_path, jobs, solver, status, ops_start)

def job_shop(slices, jobs, output_file_path):
	model = cp_model.CpModel()

	horizon = sum([op[1] for job in jobs for op in job[2]])  # Maximun time

	intervals_per_resources = collections.defaultdict(list)
	ops_start = {}  # key: (job_id, op_id), value: NewIntVar(start time of op of job)
	jobs_end = []  # value: NewIntVar(makespan of job_id)
	presences = {}  # key: (job_id, op_id, machine_id), value: selected machine of op of job

	for job_id, job in enumerate(jobs):
		ops_end = []  # end time of all operations in this job
		for op_id, op in enumerate(job[2]):
			machine, duration = op[0], op[1]  # machines and duration the op need

			# Start time and end time of this operation
			name_suffix = ' job %d op %d' % (job_id, op_id)
			start = model.NewIntVar(0, horizon, 'start' + name_suffix)
			end = model.NewIntVar(0, horizon, 'end' + name_suffix)

			ops_start[(job_id, op_id)] = start

			l_presences = []  # assigned machine (one hot)
			for m_id in range(slices):
				m_suffix = ' job %d op %d m %d' % (job_id, op_id, m_id)
				l_presence = model.NewBoolVar('presence' + m_suffix)  # Assigned to or not
				l_start = model.NewIntVar(0, horizon, 'start' + m_suffix)
				l_end = model.NewIntVar(0, horizon, 'end' + m_suffix)
				l_interval = model.NewOptionalIntervalVar(l_start, duration, l_end, l_presence, 'interval' + m_suffix)

				l_presences.append(l_presence)

				model.Add(start == l_start).OnlyEnforceIf(l_presence)  # Set op start time constraint
				model.Add(end == l_end).OnlyEnforceIf(l_presence)  # Set op end time constraint

				intervals_per_resources[m_id].append(l_interval)

				presences[(job_id, op_id, m_id)] = l_presence  # Whether op_id of job_id assigned to machine_id

			# Assign operations to enough slices
			model.Add(sum(l_presences) == machine)

			ops_end.append(end)

		# Set precedence constraints
		for op_id, op in enumerate(job[2]):
			for depend in op[2]:
				model.Add(ops_start[(job_id, op_id)] >= ops_end[depend - 1])

		# Link job end time with max(ops end time)
		job_end = model.NewIntVar(0, horizon, 'end of job %i' % job_id)
		model.AddMaxEquality(job_end, ops_end)
		jobs_end.append(job_end)

	# Machine constraints
	for m_id in range(slices):
		intervals = intervals_per_resources[m_id]
		if len(intervals) > 1:
			model.AddNoOverlap(intervals)

	# Set objective function  (scale float to fit in integer)
	weight = [int(job[0] * 10000) for job in jobs]  # w_i
	makespan = model.NewIntVar(0, horizon, 'makespan')  # max c_i
	model.AddMaxEquality(makespan, jobs_end)  # max c_i = max (end time of all jobs)
	weighted_sum = cp_model.LinearExpr.ScalProd(jobs_end, weight)  # \sum_i w_i * c_i
	model.Minimize(cp_model.LinearExpr.Sum([cp_model.LinearExpr.Term(makespan, 10000), weighted_sum]))

	# Solve
	solver = cp_model.CpSolver()
	solver.parameters.max_time_in_seconds = 60.0
	status = solver.Solve(model)

	# find all sol
	# solver = cp_model.CpSolver()
	# solution_printer = VarArraySolutionPrinterWithLimit(1)
	# status = solver.SearchForAllSolutions(model, solution_printer)

	if solver.StatusName(status) == "FEASIBLE" or solver.StatusName(status) == "OPTIMAL":
		with open(output_file_path, 'w') as f:
			for job_id, job in enumerate(jobs):
				for op_id, op in enumerate(job[2]):
					start_value = solver.Value(ops_start[(job_id, op_id)])
					print(start_value, end = ' ')
					f.write(str(start_value) + ' ')

					for m_id in range(slices):
						if solver.Value(presences[(job_id, op_id, m_id)]):
							print(m_id + 1, end = ' ')
							f.write(str(m_id + 1) + ' ')

					print()
					f.write('\n')

	
	print('Solve status: %s' % solver.StatusName(status))
	print('Optimal objective value: %i' % solver.ObjectiveValue())
	print('  - horizon: %i' % (10000* horizon))
	print('  - makespan: %i' % (10000 * solver.Value(makespan)))
	print('  - weighted sum: %i' % solver.Value(weighted_sum))
	print('Statistics')
	print('  - conflicts : %i' % solver.NumConflicts())
	print('  - branches  : %i' % solver.NumBranches())
	print('  - wall time : %f s' % solver.WallTime())

	return solver, status, ops_start

def read_input(file_path):
	jobs = []
	with open(file_path, 'r') as f:
		slices = int(f.readline().strip())
		job_num = int(f.readline().strip())

		for job_id in range(job_num):
			job = []

			op_num = int(f.readline().strip())
			job_weight = float(f.readline().strip())
			job_duration = 0

			for op_id in range(op_num):
				temp = [int(d) for d in f.readline().strip().split()]

				job.append([temp[0], temp[1], temp[3:]])
				job_duration += temp[1]

			jobs.append([job_weight, job_duration, job])

	return slices, jobs

# def write_output(file_path, jobs, solver, status, ops_start):
# 	with open(file_path, 'w') as f:
# 		for job_id, job in enumerate(jobs):
# 			for op_id, op in enumerate(job[1]):
# 				start_value = solver.Value(ops_start[(job_id, op_id)])
# 				print(start_value, end = ' ')
# 				f.write(str(start_value) + ' ')

# 				for m_id in range(slices):
# 					if solver.Value(presences[(job_id, op_id, m_id)]):
# 						print(m_id + 1, end = ' ')
# 						f.write(str(m_id + 1) + ' ')

# 				print()
# 				f.write('\n')


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
	args = parser.parse_args()
	return args

if __name__ == '__main__':
	main()
