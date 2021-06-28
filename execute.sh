#!/bin/bash
for filename in ada-private-cases/*.in; do
	name=${filename##*/}
	python3 ./challenge.py "$filename" "result/${name%.in}.out"
done
