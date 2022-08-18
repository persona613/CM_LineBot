import json

file = open('dialogue_dict.json', 'r', encoding='utf-8')
jd = json.load(file)

a = jd['補中益氣湯']

print(a)
