import pickle
import argparse
import collections
from pathlib import Path
from ortools.sat.python import cp_model

def read_input(file_path):
	jobs = []
	with open(file_path, 'r') as f:
		slices = int(f.readline().strip())
		job_num = int(f.readline().strip())

		if slices != 1:
			print("not one machine case")
			exit(0)

		for job_id in range(job_num):
			job = []

			op_num = int(f.readline().strip())
			job_weight = float(f.readline().strip())
			job_duration = 0

			for op_id in range(op_num):
				temp = [int(d) for d in f.readline().strip().split()]
				job_duration += temp[1]

			jobs.append([job_weight, job_duration])

	return slices, jobs

def _args():
	parser = argparse.ArgumentParser()
	parser.add_argument('input_path', type=Path, help='input data path')
	parser.add_argument('output_path', type=Path, help='output data path')
	args = parser.parse_args()
	return args

def main():
	args = _args()

	slices, jobs = read_input(args.input_path)
	solver, status, ops_start = job_shop(slices, jobs, args.output_path)  # solve problem
	# write_output(args.output_path, jobs, solver, status, ops_start)

def job_shop(slices, jobs, output_file_path):
	jobs = sorted(jobs, key = lambda job : job[0])
	
if __name__ == '__main__':
	main()