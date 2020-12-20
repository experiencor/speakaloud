import pymysql.cursors
import pandas as pd
import traceback
from bs4 import BeautifulSoup
from elasticsearch import helpers, Elasticsearch
import math
import argparse
from word_utils import transcribe, normalize_ipa


es = Elasticsearch()
memo = {}
connection = pymysql.connect(host='localhost',
							 user='root',
							 password='root',
							 db='speaktests',
							 charset='utf8mb4',
							 cursorclass=pymysql.cursors.DictCursor)


def update_paragraph(rows, test=True):
	all_vals = []
	for i, row in rows.iterrows():
		cols = []
		values = []
		for col in row.keys():
			cols += [col]
			if type(row[col] ) == str:
				values += ['\"' + row[col].replace('"', '\\"') + '"']
			else:
				values += [str(row[col])]
		all_vals += [values]
			
	cols = "(" + (",".join(cols)) + ")"
	vals = ",".join(["(" + ",".join(values) + ")" for values in all_vals])
	cmd = f"insert into paragraph {cols} values {vals};"
	
	try:
		with connection.cursor() as cursor:
			if test:
				print(cmd, "\n")
			else:
				cursor.execute(cmd)
			connection.commit()
	except Exception as e:
		traceback.print_exc()


def generate(dataframe):
	for _, row in dataframe.iterrows():
		ipa = normalize_ipa(" ".join([morpheme for word in row["content"].split() for ipa in transcribe(word) for morpheme in ipa]))
		yield {
			"_index": "paragraph",
			"_id": row["id"],
			"_source": {
				"level": row["level"],
				"content": row["content"],
				"ipa": ipa,
				"topic": row["topic"],
				"source": row["source"],
				"timestamp": "13-12-2020"
			}
		}


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Add paragraphs to mysql')
	parser.add_argument('-p', '--path', 		type=str, help='path to the dataframe')
	parser.add_argument('-b', '--batch-size', 	type=int, help='number of paragraphs to add at one time')
	parser.add_argument('-u', '--update', 		action='store_false', help='number of paragraphs to add at one time')

	args = parser.parse_args()

	# update the database witht the new paragraphs
	batch_size = args.batch_size
	dataframe = pd.read_csv(args.path, keep_default_na=False)
	for i in range(math.ceil(len(dataframe) / batch_size)):
		update_paragraph(dataframe.iloc[i*batch_size:(i+1)*batch_size], test=args.update)		

	# get paragraphs with ids from database
	topic = list(dataframe.topic)[0]

	with connection.cursor() as cursor:
		cmd = f"select * from paragraph where topic='{topic}';"
		cursor.execute(cmd)
		data = pd.DataFrame(cursor.fetchall())
		connection.commit()

	# index the new paragraph to elasticsearch
	helpers.bulk(es, generate(data))