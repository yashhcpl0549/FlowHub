content = open('/app/agent_executor.py').read()
old = '"local_path": file_doc["file_path"]'
new = '"gcs_path": file_doc.get("gcs_path", ""), "local_path": file_doc.get("file_path", "")'
assert old in content, "Pattern not found!"
content = content.replace(old, new)
open('/app/agent_executor.py', 'w').write(content)
print("Done — line 56 patched")
