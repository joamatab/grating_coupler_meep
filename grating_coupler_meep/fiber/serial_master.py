import subprocess

processes = []
for index in range(5):
    command = f"python compute-serial1-Copy{str(index)}.py"
    process = subprocess.Popen(command, shell=True)
    processes.append(process)
# Collect statuses
output = [p.wait() for p in processes]
print(output)
