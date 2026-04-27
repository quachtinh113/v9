import yaml
def load_yaml(p):
    with open(p, 'r') as f: return yaml.safe_load(f)
