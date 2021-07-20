# ADA Final Challenge - Flexible-Job-Shop-Scheduling
![](https://github.com/yang611/Flexible-Job-Shop-Scheduling/blob/master/ADA_ranking.png)
## FJSP intro
Flexible job shopping is an extenstion of classical job shopping problem, which allows a given task to run on any machine in the given set. Our goal is to minimize the total weighted completion time.

**Weighted total completion time**
The weighted sum of the finishing time for each job, i.e., $∑_iw_iC_i$, where $w_i$ and $C_i$ are the weight and finishing time of the $i$-th job respectively

## Method
We formulates FJSP as an integer programming problem.
Becuase it is NP-hard, we further divide it into smaller integer programming problems, which can be solved with or-tools CP-SAT solver in acceptible time. We optimize each subproblem locally then merge the results to get the final answer.

## Objective for subproblem
Optimizing locally seldom leads to global optimal. Therefore, we redesign the objective function for subproblems, which in a way allows them to consider the their global effect.

For example, we set the objective for subproblem as linear combination of **weighted total completion time** and **makespan** (ie. the total time it takes to finish the jobs). 

When scheduling the first few tasks, the **makespan** is more important because it effect the completion time for all the task after it. So the weight of **makespan** would be higher. On the other hand, in the later stage of scheduling, we put more weight on **weighted total completion time**, because there are few task after it, so the **makespan**s are not so important.

## Symmetry
When there are two identical machine available, choosing each one of them is them same. We set contraints such that the solver will always choose the machine with samller ID to reduce the exploration space, which reduce the time for optimization.

Sees "main_sym.py"
## RUN
1. run "execute.sh" to reproduce the best result
2. you can also run "main_n2.py" or "main_reweight.py" etc., which use different objective function for subproblems 