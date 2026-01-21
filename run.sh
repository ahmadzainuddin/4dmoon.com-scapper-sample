cat draw-date.txt | while read date; do
    python3 4dmoon.py "$date"
    sleep 5
done