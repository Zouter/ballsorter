import processing
import paramiko
import pickle

local = True

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
    frozenset({"orange", "green"}),
    frozenset({"blue", "yellow"}),
    frozenset({"orange"}),
    frozenset({"blue"})
]

if local:
    ssh = None
else:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("172.24.1.1", username="pi", password="framboos")

if local:
    master = processing.Master("./images/run1/", ssh, delete=False, save=False, bins=bins, gates=gates, processor_args=processor_args, decisionmaker_args=decisionmaker_args)
    master.run_local()
else:
    master = processing.Master("./tmp/", ssh, delete=False, save=False, bins=bins, gates=gates, processor_args=processor_args, decisionmaker_args=decisionmaker_args)
    master.run_camera(99999999999)
