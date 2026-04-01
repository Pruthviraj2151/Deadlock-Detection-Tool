let dependencies = [];
let cycleNodes = [];
let chart;
let deadlockCount = 0;
let network = null;

// backend state
let isDeadlockDetected = false;

// 🔥 NEW
let pendingEdge = null;

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
    const instances = parseInt(document.getElementById("instances").value) || 1;

    if (!process || !resource){
        showToast("Enter values ⚠️");
        return;
    }

    let exists = dependencies.some(d => 
        d.process === process && 
        d.resource === resource && 
        d.type === type &&
        d.instances === instances
    );

    if(exists){
        showToast("Already added ⚠️");
        return;
    }

    let temp = [...dependencies];
    temp.push({process, resource, type, instances});

    fetch("/check_safe_add", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({dependencies: temp})
    })
    .then(res => res.json())
    .then(data => {

        // 🔴 RISK → POPUP
        if(!data.safe){

            pendingEdge = {process, resource, type, instances};

            showPopup(data.message, data.suggestion || []);
            return;
        }

        // 🟢 SAFE
        dependencies.push({process, resource, type, instances});

        document.getElementById("dependencyList").innerHTML += 
        `<li>${process} → ${resource} (${type}) [${instances}]</li>`;

        drawGraph();
        updateChart();
    })
    .catch(()=>{
        showToast("Check failed ❌");
    });
}


// ================= POPUP =================
function showPopup(message, suggestions){

    document.getElementById("popup").style.display = "block";
    document.getElementById("popupMessage").innerText = message;

    let container = document.getElementById("suggestions");
    container.innerHTML = "";

    suggestions.forEach(s => {
        let div = document.createElement("div");
        div.innerText = "👉 " + s;
        container.appendChild(div);
    });
}

function closePopup(){
    document.getElementById("popup").style.display = "none";
}


// ================= CONTINUE =================
function confirmAdd(){

    if(!pendingEdge) return;

    dependencies.push(pendingEdge);

    document.getElementById("dependencyList").innerHTML += 
    `<li>${pendingEdge.process} → ${pendingEdge.resource} (${pendingEdge.type}) [${pendingEdge.instances}]</li>`;

    drawGraph();
    updateChart();

    showToast("⚠️ Added (Deadlock possible)");

    pendingEdge = null;

    closePopup();
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

        isDeadlockDetected = data.message === "❌ Deadlock Detected";

        cycleNodes = data.nodes || [];
        deadlockCount = data.count || 0;

        drawGraph();
        document.getElementById("loader").style.display="none";

        if(data.message === "❌ Deadlock Detected"){
            let reasonText = data.reason ? data.reason.join("\n") : "Circular Wait";

            alert(
`❌ DEADLOCK DETECTED

Reason:
${reasonText}

👉 Use Banker to resolve`
            );
        }

        showToast(data.message);
    })
    .catch(()=>{
        document.getElementById("loader").style.display="none";
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
            message += `\n❌ DEADLOCK DETECTED\n👉 Click BANKER to resolve`;
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
        body: JSON.stringify({ dependencies })
    })
    .then(res => res.json())
    .then(data => {

        if(data.sequence && data.sequence.length > 0){

            alert(
`✅ SAFE SEQUENCE FOUND

${data.sequence.join(" → ")}`
            );

        } else {

            alert(
`❌ UNSAFE STATE

${data.message || ""}

${data.solution ? data.solution.join("\n") : ""}`
            );
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

    const visNodes = Array.from(nodesSet).map(id => {

        let instanceLabel = "";

        if(id.startsWith("R")){
            let total = 0;

            dependencies.forEach(d => {
                if(d.resource === id && d.type === "assign"){
                    total += d.instances;
                }
            });

            if(total > 0){
                instanceLabel = ` (${total})`;
            }
        }

        return {
            id,
            label: id + instanceLabel,
            shape: id.startsWith("P") ? "box":"ellipse",
            color: cycleNodes.includes(id) ? "red" : "#17a2b8"
        };
    });

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