#!/bin/bash
for itr in {1..10}
do
healthcheck=$(curl -X GET http://localhost:8088/health | grep "OK")
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