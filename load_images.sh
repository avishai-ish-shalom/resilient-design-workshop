#!/bin/bash

for img in *.png; do
    curl -XPOST http://localhost:8881/image/${img%%.png} -H 'Content-Type: image/png' --data-binary @./${img}
    echo ''
done

echo 'Done!'