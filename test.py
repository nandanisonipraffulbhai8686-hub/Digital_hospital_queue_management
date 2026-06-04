from pymongo import MongoClient

uri = "mongodb+srv://nandanisonipraffulbhai8686_db_user:6Wl66z2lLceYWvIx@cluster0.owm0id8.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(uri)

print(client.admin.command("ping"))