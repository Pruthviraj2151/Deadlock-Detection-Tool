let dependencies = [];
let cycleNodes = [];
let chart;
let deadlockCount = 0;
let simInterval = null;

console.log("Script Loaded ✅");

// ================= TOAST =================
function showToast(msg){
    const t = document.getElementById("toast");
    t.innerText = msg;
    t.style.display="block";
    setTimeout(()=>t.style.display="none",2000);
}

// ================= STOP SIM =================
function stopSim(){
    clearInterval(simInterval);
    simInterval = null;
    showToast("Simulation Stopped ⛔");
}

// ================= START SIM =================
function autoSim(){
    if(simInterval) return;

    simInterval = setInterval(()=>{
        let p="P"+Math.floor(Math.random()*5);
        let r="R"+Math.floor(Math.random()*5);

        dependencies.push([p,r]);
        document.getElementById("dependencyList").innerHTML += `<li>${p} → ${r}</li>`;

        drawGraph();
        updateChart();
    },2000);

    showToast("Simulation Started ▶️");
}

// ================= ADD EDGE =================
function addEdge() {
    const process = document.getElementById("process").value.trim();
    const resource = document.getElementById("resource").value.trim();

    if (!process || !resource){
        showToast("Enter values ⚠️");
        return;
    }

    dependencies.push([process, resource]);
    document.getElementById("dependencyList").innerHTML += `<li>${process} → ${resource}</li>`;

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

// ================= 🔥 SMART AI =================
function predictAI() {
    fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dependencies })
    })
    .then(res => res.json())
    .then(data => {

        let solutionText = "";
        data.solution.forEach(s => {
            solutionText += "• " + s + "\n";
        });

        alert(`
AI Deadlock Prediction

Risk: ${data.risk}

${data.message}

Reason:
${data.reason}

Solution:
${solutionText}

Processes: ${data.metrics.processes}
Resources: ${data.metrics.resources}
Edges: ${data.metrics.edges}
Density: ${data.metrics.density}
        `);

        document.getElementById("metrics").innerText =
        `Processes: ${data.metrics.processes}
Resources: ${data.metrics.resources}
Edges: ${data.metrics.edges}
Density: ${data.metrics.density}
Deadlocks: ${deadlockCount}`;
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
        alert(data.message);
    })
    .catch(()=>{
        alert("Banker failed ❌");
    });
}

// ================= GRAPH =================
function drawGraph() {
    const nodesSet = new Set();
    dependencies.forEach(([f,t]) => {
        nodesSet.add(f);
        nodesSet.add(t);
    });

    const visNodes = Array.from(nodesSet).map(id => ({
        id,
        label:id,
        shape: id.startsWith("P") ? "box":"ellipse",
        color: cycleNodes.includes(id) ? "red" : "#17a2b8"
    }));

    const visEdges = dependencies.map(([f,t]) => ({
        from:f,
        to:t,
        arrows:"to"
    }));

    new vis.Network(
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

// ================= FEEDBACK =================
document.addEventListener("DOMContentLoaded", function(){
    const form = document.getElementById("feedbackForm");

    if(form){
        form.addEventListener("submit", function(e){
            e.preventDefault();

            const formData = new FormData(form);

            fetch("https://formspree.io/f/manelney", {
                method: "POST",
                body: formData
            })
            .then(res=>{
                if(res.ok){
                    document.getElementById("feedbackResponse").innerText = "✅ Feedback submitted!";
                    form.reset();
                } else {
                    document.getElementById("feedbackResponse").innerText = "❌ Failed";
                }
            });
        });
    }
});

// ================= DARK MODE =================
function toggleMode(){
    document.body.classList.toggle("light-mode");
}

// ================= RESET =================
function resetAll(){
    location.reload();
}