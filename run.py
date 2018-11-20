import processing
import paramiko
import pickle

local = False

colorbin_models = pickle.load(open("colorbin_models.pkl", "rb"))
knn_model = pickle.load(open("knn_model.pkl", "rb"))

processor_args = {"colorbin_models":colorbin_models}
decisionmaker_args = {"knn_model":knn_model}

bins = [
    "orange",
    "blue",
    "yellow",
    "green"
]

gates = [
    frozenset({"#0074D9"}),
    frozenset({"#FF851B", "#0074D9"}),
    frozenset({"#FF851B", "#228B22"}),
    frozenset({"#FFDC00"}),
    frozenset({"#FFDC00", "#0074D9"})
]

pictures = ["blue", "blue_orange", "green_orange", "yellow", "yellow_blue"]

if local:
    ssh = None
else:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("172.24.1.1", username="pi", password="framboos", allow_agent=False, look_for_keys=False)

if ssh:
    processing.stop_framboos(ssh)
    ssh.exec_command("fuser 8001/tcp -k") # kill everyone listening at 8001
    stdin, stdout, stderr = ssh.exec_command("python3 flow2/sorter.py &") # start sorter socket at pi

if local:
    master = processing.Master("./images/run235/", ssh, delete=False, save=False, bins=bins, gates=gates, pictures=pictures, processor_args=processor_args, decisionmaker_args=decisionmaker_args)
    master.run_local()
else:
    master = processing.Master("./images/run6/", ssh, delete=False, save=False, bins=bins, gates=gates, pictures=pictures, processor_args=processor_args, decisionmaker_args=decisionmaker_args)
    master.run_camera(99999999999999)
