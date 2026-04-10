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


# ================= DEADLOCK LOGIC =================
def check_deadlock_real(dependencies):

    processes = list(set([d['process'] for d in dependencies]))
    resources = list(set([d['resource'] for d in dependencies]))

    p_index = {p:i for i,p in enumerate(processes)}
    r_index = {r:i for i,r in enumerate(resources)}

    n = len(processes)
    m = len(resources)

    allocation = [[0]*m for _ in range(n)]
    request = [[0]*m for _ in range(n)]

    for dep in dependencies:
        p = dep['process']
        r = dep['resource']
        t = dep['type']
        inst = dep.get('instances', 1)

        if t == "assign":
            allocation[p_index[p]][r_index[r]] += inst
        else:
            request[p_index[p]][r_index[r]] += inst

    resource_total = {}
    for dep in dependencies:
        if dep['type'] == "assign":
            r = dep['resource']
            inst = dep.get('instances', 1)

            if r not in resource_total:
                resource_total[r] = inst
            else:
                resource_total[r] += inst

    total_instances = [resource_total.get(r, 0) for r in resources]

    available = total_instances[:]
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

    deadlocked_processes = [processes[i] for i in range(n) if not finish[i]]

    if len(deadlocked_processes) == 0:
        return False, []

    if len(deadlocked_processes) == n:
        return True, deadlocked_processes

    return False, []


# ================= 🔥 FIXED ROUTE =================
@app.route('/check_safe_add', methods=['POST'])
def check_safe_add():
    data = request.json
    dependencies = data.get('dependencies', [])

    has_deadlock, _ = check_deadlock_real(dependencies)

    if has_deadlock:

        all_resources = list(set(d["resource"] for d in dependencies))

        try_suggestions = []
        remove_suggestions = []

        last = dependencies[-1]
        process = last["process"]
        current_resource = last["resource"]
        type_ = last["type"]
        instances = last.get("instances", 1)

        # 🔥 TRY CHANGE RESOURCE
        for r in all_resources:
            if r == current_resource:
                continue

            temp = dependencies.copy()
            temp[-1] = {
                "process": process,
                "resource": r,
                "type": type_,
                "instances": instances
            }

            deadlock, _ = check_deadlock_real(temp)

            if not deadlock:
                try_suggestions.append(f"Try {process} → {r}")

        # 🔥 TRY REMOVE EDGE
        for dep in dependencies:
            temp = dependencies.copy()
            temp.remove(dep)

            deadlock, _ = check_deadlock_real(temp)

            if not deadlock:
                remove_suggestions.append(f"Remove {dep['process']} → {dep['resource']}")

        # 🔥 FINAL COMBINE (YOUR FIX)
        suggestions = []

        if try_suggestions:
            suggestions.append(try_suggestions[0])

        if remove_suggestions:
            suggestions.append(remove_suggestions[0])

        if not suggestions:
            suggestions = ["Reduce instances", "Release some resources"]

        return jsonify({
            "safe": False,
            "message": "⚠️ Adding this may cause DEADLOCK",
            "suggestion": suggestions
        })

    else:
        return jsonify({
            "safe": True,
            "message": "✅ Safe to add"
        })


# ================= REASON =================
def get_deadlock_reason(dependencies):
    reasons = []

    processes = set(d['process'] for d in dependencies)

    for p in processes:
        has_assign = any(d['process']==p and d['type']=="assign" for d in dependencies)
        has_request = any(d['process']==p and d['type']=="request" for d in dependencies)
        if has_assign and has_request:
            reasons.append("Hold and Wait")
            break

    resource_used = {}
    for d in dependencies:
        if d['type']=="assign":
            r = d['resource']
            resource_used[r] = resource_used.get(r,0)+1

    if any(v >= 1 for v in resource_used.values()):
        reasons.append("Mutual Exclusion")

    reasons.append("No Preemption")

    import networkx as nx
    G = nx.DiGraph()

    for d in dependencies:
        if d['type'] == "assign":
            G.add_edge(d['resource'], d['process'])
        else:
            G.add_edge(d['process'], d['resource'])

    try:
        nx.find_cycle(G)
        reasons.append("Circular Wait")
    except:
        pass

    return reasons


# ================= ROUTES =================
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
            'count': deadlock_count,
            'reason': get_deadlock_reason(dependencies)
        })

    else:
        return jsonify({
            'message': '✅ Safe System',
            'nodes': [],
            'count': deadlock_count,
            'reason': get_deadlock_reason(dependencies)
        })


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
            'message': '❌ Deadlock WILL occur'
        })

    elif pred == 1:
        return jsonify({
            'risk': 'MEDIUM',
            'deadlock': False,
            'message': '⚠️ Risky system'
        })

    else:
        return jsonify({
            'risk': 'LOW',
            'deadlock': False,
            'message': '✅ Safe system'
        })


@app.route('/banker', methods=['POST'])
def banker():
    data = request.json
    deps = data.get('dependencies', [])

    if not deps:
        return jsonify({'message': '⚠️ No data'})

    processes = list(set([d['process'] for d in deps]))
    resources = list(set([d['resource'] for d in deps]))

    p_index = {p:i for i,p in enumerate(processes)}
    r_index = {r:i for i,r in enumerate(resources)}

    n = len(processes)
    m = len(resources)

    allocation = [[0]*m for _ in range(n)]
    max_need = [[0]*m for _ in range(n)]

    resource_total = {}

    for dep in deps:
        p = dep['process']
        r = dep['resource']
        t = dep['type']
        inst = dep.get('instances',1)

        if t == "assign":
            allocation[p_index[p]][r_index[r]] += inst

            if r not in resource_total:
                resource_total[r] = inst
            else:
                resource_total[r] += inst

        if t == "request":
            max_need[p_index[p]][r_index[r]] += inst

    for i in range(n):
        for j in range(m):
            max_need[i][j] += allocation[i][j]

    total_instances = [resource_total.get(r,0) for r in resources]

    available = total_instances[:]
    for i in range(n):
        for j in range(m):
            available[j] -= allocation[i][j]

    need = [[max_need[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]

    finish = [False]*n
    safe_seq = []
    work = available[:]

    while len(safe_seq) < n:
        found = False

        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                for j in range(m):
                    work[j] += allocation[i][j]

                safe_seq.append(processes[i])
                finish[i] = True
                found = True

        if not found:
            problem_process = processes[0] if processes else "P0"

            return jsonify({
                'message': '❌ Unsafe State',
                'solution': [
                    f'Kill process {problem_process}',
                    'Release its resources',
                    'Re-run Banker Algorithm'
                ]
            })

    return jsonify({
        'message': '✅ Safe Sequence Found',
        'sequence': safe_seq
    })


@app.route('/')
def home():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
    # updated