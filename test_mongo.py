from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
print(client.admin.command("ping"))  # Should return {'ok': 1.0}
