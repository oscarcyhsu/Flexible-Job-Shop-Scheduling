# ADA Final Challenge - Flexible-Job-Shop-Scheduling
![](https://github.com/yang611/Flexible-Job-Shop-Scheduling/blob/master/img/ADA_ranking.png)
## FJSP intro
Flexible job shopping is an extenstion of classical job shopping problem, which allows a given task to run on any machine in the given set. In this challenge , we also generalize the matric to optimize.

**Makespan**
The total time required to finish all the jobs.

**weighted total completion time**
![](https://github.com/yang611/Flexible-Job-Shop-Scheduling/blob/master/img/formula.png =900x)



Our goal is to minimize the sum of makespan total weighted completion time.
![](https://github.com/yang611/Flexible-Job-Shop-Scheduling/blob/master/img/objective.png =140x)


## Method
We formulates FJSP as an integer programming problem.
Becuase it is NP-hard, we further divide it into smaller integer programming problems, which can be solved with or-tools CP-SAT solver in acceptible time. We optimize each subproblem locally then merge the results to get the final answer.

## Objective for subproblem
Optimizing locally seldom leads to global optimal. Therefore, we redesign the objective function for subproblems, which in a way allows them to consider the their global effect.

For example, we change the coefficient of **weighted total completion time** and **makespan** (ie. the total time it takes to finish the jobs). 

When scheduling the first few tasks, the **makespan** is more important because it effect the completion time for all the task after it. So the weight of **makespan** would be higher. On the other hand, in the later stage of scheduling, we put more weight on **weighted total completion time**, because there are few tasks after it, so the **makespan**s are not so important.

## Symmetry
When there are two identical machine available, choosing each one of them is them same. We set contraints such that the solver will always choose the machine with samller ID to reduce the exploration space, which reduce the time for optimization.

Sees "main_sym.py"
## RUN
1. run "execute.sh" to reproduce the best result
2. you can also run "main_n2.py" or "main_reweight.py" etc., which use different objective function for subproblems 