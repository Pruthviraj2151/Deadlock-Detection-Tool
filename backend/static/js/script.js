let dependencies = [];
let cycleNodes = [];
let chart;
let deadlockCount = 0;
let network = null;

console.log("Script Loaded ✅");

// ================= TOAST =================
function showToast(msg){
    const t = document.getElementById("toast");
    t.innerText = msg;
    t.style.display="block";
    setTimeout(()=>t.style.display="none",2000);
}

// ================= ADD EDGE =================
function addEdge() {
    const process = document.getElementById("process").value.trim();
    const resource = document.getElementById("resource").value.trim();
    const type = document.getElementById("type").value;

    // 🔥 NEW LINE (instances)
    const instances = parseInt(document.getElementById("instances").value) || 1;

    if (!process || !resource){
        showToast("Enter values ⚠️");
        return;
    }

    // ✅ Prevent exact duplicate
    let exists = dependencies.some(d => 
        d.process === process && 
        d.resource === resource && 
        d.type === type
    );

    if(exists){
        showToast("Already added ⚠️");
        return;
    }

    // ✅ Correct validation fix
    let invalid = dependencies.some(d =>
        d.process === process &&
        d.resource === resource &&
        d.type === "assign" &&
        type === "request"
    );

    if(invalid){
        showToast("Invalid: Process already holding resource ⚠️");
        return;
    }

    // 🔥 UPDATED PUSH (instances added)
    dependencies.push({
        process,
        resource,
        type,
        instances
    });

    document.getElementById("dependencyList").innerHTML += 
    `<li>${process} → ${resource} (${type}) [${instances}]</li>`;

    drawGraph();
    updateChart();
}

// ================= DEADLOCK =================
function detectDeadlock() {
    document.getElementById("loader").style.display="block";

    fetch("/detect_deadlock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dependencies })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("result").innerText = data.message;
        cycleNodes = data.nodes || [];
        deadlockCount = data.count || 0;

        drawGraph();
        document.getElementById("loader").style.display="none";

        showToast(data.message);
    })
    .catch(()=>{
        showToast("Deadlock Error ❌");
    });
}

// ================= AI =================
function predictAI() {
    fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dependencies })
    })
    .then(res => res.json())
    .then(data => {

        let message = `
AI RESULT

Risk: ${data.risk}

${data.message}
`;

        if(data.deadlock){
            message += `\n❌ DEADLOCK DETECTED`;
            message += `\n👉 Click BANKER to resolve`;
        } else {
            message += `\n✅ NO DEADLOCK`;
        }

        alert(message);

        document.getElementById("metrics").innerText =
        `Risk: ${data.risk}
Deadlock: ${data.deadlock ? "YES" : "NO"}
Dependencies: ${dependencies.length}`;
    })
    .catch(()=>{
        alert("AI prediction failed ❌");
    });
}

// ================= BANKER =================
function runBanker(){
    fetch("/banker", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            allocation:[[0,1],[2,0]],
            max:[[1,2],[2,1]],
            available:[1,1]
        })
    })
    .then(res => res.json())
    .then(data => {

        if(data.sequence){
            alert(`
✅ SAFE SEQUENCE FOUND

${data.sequence.join(" → ")}
            `);
        } else {
            alert(data.message);
        }
    })
    .catch(()=>{
        alert("Banker failed ❌");
    });
}

// ================= GRAPH =================
function drawGraph() {

    const nodesSet = new Set();

    dependencies.forEach(dep => {
        nodesSet.add(dep.process);
        nodesSet.add(dep.resource);
    });

    const visNodes = Array.from(nodesSet).map(id => ({
        id,
        label:id,
        shape: id.startsWith("P") ? "box":"ellipse",
        color: cycleNodes.includes(id) ? "red" : "#17a2b8"
    }));

    const visEdges = dependencies.map(dep => ({
        from: dep.type === "assign" ? dep.resource : dep.process,
        to: dep.type === "assign" ? dep.process : dep.resource,
        arrows:"to",
        color: dep.type === "assign" ? "green" : "orange"
    }));

    if(network) network.destroy();

    network = new vis.Network(
        document.getElementById("network"),
        {nodes:visNodes,edges:visEdges},
        {}
    );
}

// ================= CHART =================
function updateChart(){
    if(chart) chart.destroy();

    const ctx = document.getElementById("chart");

    chart = new Chart(ctx,{
        type:'bar',
        data:{
            labels:['Dependencies'],
            datasets:[{
                label:'Edges',
                data:[dependencies.length],
                backgroundColor:'#ff7b00'
            }]
        }
    });
}

// ================= DARK MODE =================
function toggleMode(){
    document.body.classList.toggle("light-mode");
}

// ================= RESET =================
function resetAll(){
    location.reload();
}