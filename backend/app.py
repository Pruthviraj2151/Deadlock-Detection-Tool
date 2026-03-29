from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
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


# ================= 🔥 REAL DEADLOCK (MULTI-INSTANCE FIX) =================
def check_deadlock_real(dependencies):

    processes = list(set([d['process'] for d in dependencies]))
    resources = list(set([d['resource'] for d in dependencies]))

    p_index = {p:i for i,p in enumerate(processes)}
    r_index = {r:i for i,r in enumerate(resources)}

    n = len(processes)
    m = len(resources)

    allocation = [[0]*m for _ in range(n)]
    request = [[0]*m for _ in range(n)]

    # Build matrices
    for dep in dependencies:
        p = dep['process']
        r = dep['resource']
        t = dep['type']

        if t == "assign":
            allocation[p_index[p]][r_index[r]] += 1
        else:
            request[p_index[p]][r_index[r]] += 1

    # 🔥 MULTI-INSTANCE SUPPORT (ONLY CHANGE)
    available = [0]*m

    for dep in dependencies:
        r = dep['resource']
        inst = dep.get('instances', 1)
        available[r_index[r]] = max(available[r_index[r]], inst)

    # Subtract allocated resources
    for i in range(n):
        for j in range(m):
            available[j] -= allocation[i][j]

    finish = [False]*n

    while True:
        found = False

        for i in range(n):
            if not finish[i] and all(request[i][j] <= available[j] for j in range(m)):
                for j in range(m):
                    available[j] += allocation[i][j]
                finish[i] = True
                found = True

        if not found:
            break

    if all(finish):
        return False, []   # SAFE
    else:
        return True, []    # DEADLOCK


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

    has_deadlock, nodes = check_deadlock_real(dependencies)

    if has_deadlock:
        deadlock_count += 1
        return jsonify({
            'message': '❌ Deadlock Detected',
            'nodes': nodes,
            'count': deadlock_count
        })
    else:
        return jsonify({
            'message': '✅ Safe System',
            'nodes': [],
            'count': deadlock_count
        })


# ================= 🔥 AI SMART =================
@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    deps = data.get('dependencies', [])

    if not deps:
        return jsonify({
            'risk': 'LOW',
            'deadlock': False,
            'message': 'System is empty and safe'
        })

    has_deadlock, _ = check_deadlock_real(deps)

    processes = len(set([d['process'] for d in deps]))
    resources = len(set([d['resource'] for d in deps]))
    edges = len(deps)
    density = edges / (processes + resources + 1)

    pred = model.predict([[processes, resources, edges, density]])[0]

    if has_deadlock:
        return jsonify({
            'risk': 'HIGH',
            'deadlock': True,
            'message': '❌ Deadlock WILL occur (unsafe state)',
            'solution': [
                'Run Banker Algorithm',
                'Kill a process',
                'Release resources'
            ]
        })

    elif pred == 1:
        return jsonify({
            'risk': 'MEDIUM',
            'deadlock': False,
            'message': '⚠️ Risky system (may lead to deadlock)'
        })

    else:
        return jsonify({
            'risk': 'LOW',
            'deadlock': False,
            'message': '✅ System is safe'
        })


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
        allocated_flag = False

        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                for j in range(m):
                    work[j] += allocation[i][j]

                safe_seq.append(f"P{i}")
                finish[i] = True
                allocated_flag = True

        if not allocated_flag:
            return jsonify({'message': '❌ Unsafe State (Deadlock Cannot be Resolved)'})

    return jsonify({
        'message': '✅ Safe Sequence Found',
        'sequence': safe_seq
    })


# ================= HOME =================
@app.route('/')
def home():
    return render_template('index.html')


# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)