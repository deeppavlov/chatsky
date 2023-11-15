#!/bin/bash
if [[ $# = 0 ]] ; then printf "Specify healthcheck url;\n"; exit 1; fi;
for itr in {1..10}
do
healthcheck=$(curl -X GET "${1}" | grep "OK")
healthcheck=$?
if [ "$healthcheck" -ne 0 ] ; then
echo "Healthcheck failed. sleeping for 5 secs"
sleep 5
echo 'Iteration' $itr
if [ $itr == 10 ]; then
echo 'Healthcheck suite unsuccessful.'
fi
else
echo "Healthcheck suite succesful."
break
exit 0
fi
done