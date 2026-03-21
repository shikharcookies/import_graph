document.addEventListener("DOMContentLoaded", () => {
    const FOLDER_COUNT = document.getElementById("folder-count");
    const FILE_COUNT = document.getElementById("file-count");
    const SEARCH_BOX = document.getElementById("search-box");
    const UPLOAD_JSON = document.getElementById("upload-json");
    const NODE_DETAILS = document.getElementById("node-details");
    const BREADCRUMB = document.getElementById("breadcrumb");
    const SVG = d3.select("#graph");
    
    let colorScale, allNodes, allEdges, metaData, indirectDeps;
    let navigationHistory = [];

    // Load default if available
    fetch("dependency_data.json")
        .then(response => response.json())
        .then(data => initialize(data))
        .catch(err => console.log("No default JSON found. Please upload one."));

    UPLOAD_JSON.addEventListener("change", (event) => {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const data = JSON.parse(e.target.result);
            initialize(data);
        };
        reader.readAsText(file);
    });

    function initialize(data) {
        const { meta, nodes, edges, indirect_dependencies } = data;
        allNodes = nodes;
        allEdges = edges;
        metaData = meta;
        indirectDeps = indirect_dependencies || {};
        navigationHistory = [];

        FOLDER_COUNT.textContent = meta.folders.length;
        FILE_COUNT.textContent = meta.total_files;

        colorScale = d3.scaleOrdinal(d3.schemeTableau10);
        meta.folders.forEach((folder, i) => colorScale(i));

        updateBreadcrumb();
        
        const focusText = metaData.focus_folder || "SPEScripts";
        SEARCH_BOX.placeholder = `Search for a file in ${focusText}...`;
        
        // Show blank state or search instruction
        SVG.selectAll("*").remove();
        SVG.append("text")
            .attr("x", "50%")
            .attr("y", "50%")
            .attr("text-anchor", "middle")
            .attr("fill", "#888")
            .text(`Search for a file in ${focusText} to start exploring`);
    }

    SEARCH_BOX.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            const searchTerm = SEARCH_BOX.value.trim().toLowerCase();
            const matchingNode = allNodes.find(n => 
                n.label.toLowerCase() === searchTerm || 
                n.id.toLowerCase().includes(searchTerm)
            );
            if (matchingNode) {
                navigateTo(matchingNode.id);
            } else {
                alert("File not found. Try 'abc.py'");
            }
        }
    });

    function navigateTo(rootId) {
        if (navigationHistory.includes(rootId)) {
            const index = navigationHistory.indexOf(rootId);
            navigationHistory = navigationHistory.slice(0, index + 1);
        } else {
            navigationHistory.push(rootId);
        }
        updateBreadcrumb();
        displayTree(rootId);
    }

    function updateBreadcrumb() {
        BREADCRUMB.innerHTML = "";
        navigationHistory.forEach((id, i) => {
            const node = allNodes.find(n => n.id === id);
            const span = document.createElement("span");
            span.className = "crumb";
            span.textContent = node.label;
            span.onclick = () => navigateTo(id);
            BREADCRUMB.appendChild(span);
            if (i < navigationHistory.length - 1) {
                const sep = document.createElement("span");
                sep.textContent = " > ";
                BREADCRUMB.appendChild(sep);
            }
        });
    }

    function displayTree(rootId) {
        const rootNode = allNodes.find(n => n.id === rootId);
        if (!rootNode) return;

        // Find direct children (imports)
        const children = allEdges
            .filter(e => e.source === rootId)
            .map(e => {
                const targetNode = allNodes.find(n => n.id === e.target);
                return { ...targetNode, import_statement: e.import_statement };
            });

        const treeData = { ...rootNode, children };
        const WIDTH = SVG.node().getBoundingClientRect().width;
        const HEIGHT = SVG.node().getBoundingClientRect().height;

        SVG.selectAll("*").remove();

        const root = d3.hierarchy(treeData);
        // Single-level tree
        const treeLayout = d3.tree().size([HEIGHT - 100, WIDTH - 400]);
        treeLayout(root);

        const g = SVG.append("g").attr("transform", "translate(200, 50)");

        // Links
        g.selectAll('path')
            .data(root.links())
            .enter()
            .append('path')
            .attr('d', d3.linkHorizontal()
                .x(d => d.y)
                .y(d => d.x)
            )
            .attr("fill", "none")
            .attr("stroke", "#ccc")
            .attr("stroke-width", 2);

        // Nodes
        const node = g.selectAll("g")
            .data(root.descendants())
            .join("g")
            .attr("transform", d => `translate(${d.y},${d.x})`)
            .on("click", (event, d) => {
                if (d.data.type === "internal") {
                    navigateTo(d.data.id);
                } else {
                    showNodeDetails(d.data, allEdges);
                }
            });

        node.append("circle")
            .attr("r", d => d.depth === 0 ? 15 : 10)
            .attr("fill", d => d.data.folder_index !== -1 ? colorScale(d.data.folder_index) : "#eee")
            .attr("stroke", "#333")
            .attr("class", d => d.depth === 0 ? "glow" : "");

        node.append("text")
            .text(d => d.data.label)
            .attr("x", d => d.children ? -15 : 15)
            .attr("y", 5)
            .attr("text-anchor", d => d.children ? "end" : "start")
            .style("font-weight", d => d.depth === 0 ? "bold" : "normal");

        showNodeDetails(rootNode, allEdges);
    }

    function showNodeDetails(d, edges) {
        const imports = edges.filter(e => e.source === d.id);
        const importedBy = edges.filter(e => e.target === d.id);
        const fileIndirect = indirectDeps[d.id] || [];

        const meta = {
            committer: d.committer,
            date: d.commit_date,
            jira: d.jira_number
        };

        NODE_DETAILS.innerHTML = `
            <div class="detail-card">
                <h2 style="color: ${d.folder_index !== -1 ? colorScale(d.folder_index) : '#666'}">${d.label}</h2>
                <hr>
                <p><strong>Type:</strong> <span class="badge ${d.type}">${d.type}</span></p>
                ${d.folder ? `<p><strong>Folder:</strong> ${d.folder}</p>` : ""}
                ${d.full_path ? `<p><strong>Path:</strong> <small>${d.full_path}</small></p>` : ""}
                ${meta.committer || meta.date || meta.jira ? `<hr>
                <h4>Bitbucket info</h4>
                <ul class="detail-list">
                ${meta.committer ? `<p><strong>Committer:</strong> ${meta.committer}</p>` : ""}
                ${meta.date ? `<p><strong>Date:</strong> ${meta.date}</p>` : ""}
                ${meta.jira ? `<p><strong>JIRA:</strong> ${meta.jira}</p>` : ""}
                </ul>
                `: ""}
                <hr>
                <h4>Direct Imports (${imports.length})</h4>
                <ul class="detail-list">
                    ${imports.map(i => {
                        const target = allNodes.find(n => n.id === i.target);
                        return `<li>${target.label} <br><small class="stmt">${i.import_statement}</small></li>`;
                    }).join("")}
                </ul>
                ${fileIndirect.length > 0 ? `
                <hr>
                <h4>Indirect Usage (${fileIndirect.length})</h4>
                <ul class="detail-list">
                    ${fileIndirect.map(chain => `<li><small class="stmt">${chain}</small></li>`).join("")}
                </ul>` : ""}
                <hr>
                <h4>Imported By (${importedBy.length})</h4>
                <ul class="detail-list">
                    ${importedBy.map(i => {
                        const src = allNodes.find(n => n.id === i.source);
                        return `<li>${src.label}</li>`;
                    }).join("")}
                </ul>
            </div>
        `;
    }
});

