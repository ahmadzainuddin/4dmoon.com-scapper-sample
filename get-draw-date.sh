curl -s https://www.damacai.com.my/ListPastResult \
| jq -r '.drawdate' \
| tr ' ' '\n' \
| sed '/^$/d' \
| sed 's/\(....\)\(..\)\(..\)/\1-\2-\3/' \
> draw-date.txt

# Clean date already processed
python3 clean_draw_date.py draw-date.txt