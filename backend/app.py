from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import networkx as nx
import joblib
import numpy as np

app = Flask(__name__)
CORS(app)

deadlock_count = 0

# ================= AI MODEL =================
try:
    model = joblib.load('model.pkl')
except:
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier()

    X = np.array([
        [2,1,1,0.2],
        [4,2,2,0.5],
        [6,3,3,0.8],
        [8,4,4,1.2]
    ])
    y = [0,0,1,1]

    model.fit(X,y)
    joblib.dump(model,'model.pkl')

# ================= DEADLOCK =================
@app.route('/detect_deadlock', methods=['POST'])
def detect_deadlock():
    global deadlock_count

    data = request.json
    dependencies = data.get('dependencies', [])

    if not dependencies:
        return jsonify({
            'message': '⚠️ No dependencies',
            'nodes': [],
            'count': deadlock_count
        })

    G = nx.DiGraph()
    owner = {}

    for p,r in dependencies:
        if r not in owner:
            owner[r] = p
            G.add_edge(r,p)
        else:
            G.add_edge(p,r)

    try:
        cycle = nx.find_cycle(G)
        nodes = [i[0] for i in cycle]

        deadlock_count += 1

        return jsonify({
            'message': '❌ Deadlock Detected',
            'nodes': nodes,
            'count': deadlock_count
        })

    except nx.NetworkXNoCycle:
        return jsonify({
            'message': '✅ Safe System',
            'nodes': [],
            'count': deadlock_count
        })

# ================= AI SMART =================


@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    deps = data.get('dependencies', [])

    if not deps:
        return jsonify({
            'risk': 'LOW',
            'message': 'System is empty and safe',
            'reason': 'No dependencies present',
            'solution': ['No action needed'],
            'metrics': {
                'processes': 0,
                'resources': 0,
                'edges': 0,
                'density': 0
            }
        })

    processes = len(set([p for p,_ in deps]))
    resources = len(set([r for _,r in deps]))
    edges = len(deps)

    density = edges / (processes + resources + 1)

    pred = model.predict([[processes, resources, edges, density]])[0]

    if pred == 1:
        return jsonify({
            'risk': 'HIGH',
            'message': '⚠️ Deadlock may occur soon!',
            'reason': 'High dependency density & circular wait possible',
            'solution': [
                'Apply Banker’s Algorithm',
                'Reduce resource sharing',
                'Avoid circular wait',
                'Increase available resources'
            ],
            'metrics': {
                'processes': processes,
                'resources': resources,
                'edges': edges,
                'density': round(density,2)
            }
        })
    else:
        return jsonify({
            'risk': 'LOW',
            'message': '✅ System is safe',
            'reason': 'Low dependency and no circular wait',
            'solution': ['No action required'],
            'metrics': {
                'processes': processes,
                'resources': resources,
                'edges': edges,
                'density': round(density,2)
            }
        })

# ================= BANKER =================
# ================= BANKER =================
@app.route('/banker', methods=['POST'])
def banker():
    data = request.json

    allocation = data.get('allocation')
    max_need = data.get('max')
    available = data.get('available')

    if not allocation or not max_need or not available:
        return jsonify({'message': '⚠️ Missing data for Banker'})

    n = len(allocation)
    m = len(available)

    need = [[max_need[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]

    finish = [False]*n
    safe_seq = []
    work = available[:]

    while len(safe_seq) < n:
        allocated = False

        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):

                for j in range(m):
                    work[j] += allocation[i][j]

                safe_seq.append(f"P{i}")
                finish[i] = True
                allocated = True

        if not allocated:
            return jsonify({'message': '❌ Unsafe State (Deadlock Possible)'})

    return jsonify({
        'message': '✅ Safe Sequence Found',
        'sequence': safe_seq
    })

# ================= HOME =================
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
