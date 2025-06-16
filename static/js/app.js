// Global variables - VERSION 3.0 (IMPROVED VERSION)
console.log("Loading TracLine Dashboard JS v3.0 (IMPROVED VERSION)");
let currentProject = null;
let projects = [];
let members = [];
let tasks = [];
let currentCropper = null;
let currentMemberId = null;
let autoRefreshInterval = null;
let isAutoRefreshEnabled = true;
let REFRESH_INTERVAL = 10000; // 10 seconds
let currentViewMode = localStorage.getItem('teamViewMode') || 'pyramid'; // Default view mode: pyramid, list, or tile

// Global function for changing view mode
function changeViewMode(mode) {
    console.log("changeViewMode called with mode:", mode);
    // Update currentViewMode
    currentViewMode = mode;
    
    // Update the root element directly
    const root = document.getElementById('team-hierarchy');
    if (root) {
        // Remove all view mode classes
        root.classList.remove('view-pyramid', 'view-list', 'view-tile');
        // Add the new view mode class
        root.classList.add(`view-${mode}`);
        
        console.log(`Applied view-${mode} class to team-hierarchy`);
    } else {
        console.error('team-hierarchy element not found');
    }
    
    // Update button appearance
    const buttons = document.querySelectorAll('.mode-btn');
    buttons.forEach(btn => {
        if (btn.dataset.mode === mode) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Save preference to localStorage
    localStorage.setItem('teamViewMode', mode);
    
    // Reload the team data to apply the new view mode
    loadTeamData();
}

// (Making functions global moved to end of file)

document.addEventListener('DOMContentLoaded', () => {
    console.log('TracLine Web Interface initializing...');
    
    // Load projects first
    loadProjects();
    setupTabs();
    setupModals();
    setupFilters();
    setupAutoRefresh();
    
    // Debug information
    console.log('DOM elements:');
    console.log('- project-select:', document.getElementById('project-select'));
    console.log('- team-hierarchy:', document.getElementById('team-hierarchy'));
    console.log('- tasks-list:', document.getElementById('tasks-list'));
    console.log('- matrix-container:', document.getElementById('matrix-container'));
    
    // Force load data directly for testing
    setTimeout(() => {
        const projectId = 'test-project';
        console.log(`Forcing load of test-project data`);
        currentProject = projectId;
        
        // Select in dropdown
        const select = document.getElementById('project-select');
        if (select) select.value = projectId;
        
        // Force load all tabs
        loadTeamData();
        loadTasksData();
        loadMatrixData();
    }, 1000);
});

// View mode switching is now handled by inline script in HTML
// This function is kept for backward compatibility but doesn't do anything
function addViewModeSwitcher() {
    console.log("View mode switcher is now handled by inline HTML script");
    return; // Do nothing, as this is now handled directly in HTML
}

// Show update indicator
function showUpdateIndicator(message) {
    const indicator = document.createElement('div');
    indicator.className = 'refresh-indicator';
    indicator.textContent = message;
    document.body.appendChild(indicator);
    
    setTimeout(() => {
        indicator.remove();
    }, 3000);
}

// Tab switching
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            console.log(`Tab clicked: ${tabName}`);

            // Remove active class from all buttons and contents
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');

            // Load data for the active tab
            if (tabName === 'team' && currentProject) {
                loadTeamData();
            } else if (tabName === 'tasks' && currentProject) {
                loadTasksData();
            } else if (tabName === 'matrix' && currentProject) {
                loadMatrixData();
            }
        });
    });
}

// Setup modals
function setupModals() {
    // Get all modals
    const modals = document.querySelectorAll('.modal');
    
    // Get all close buttons
    const closeButtons = document.querySelectorAll('.close');
    
    // Add click event to close buttons
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            button.closest('.modal').style.display = 'none';
        });
    });
    
    // Click outside modal to close
    window.addEventListener('click', (event) => {
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

// Setup filters
function setupFilters() {
    const applyButton = document.getElementById('apply-filters');
    if (applyButton) {
        applyButton.addEventListener('click', () => {
            loadTasksData();
        });
    }
}

// Load projects
async function loadProjects() {
    try {
        console.log('Loading projects...');
        const response = await fetch('/api/projects');
        const projectData = await response.json();
        console.log('Projects response:', projectData);
        
        // Handle both array and object response
        projects = Array.isArray(projectData) ? projectData : projectData.projects || [];
        console.log('Loaded projects:', projects);
        
        const select = document.getElementById('project-select');
        if (!select) {
            console.error('Project select element not found!');
            return;
        }
        
        select.innerHTML = '<option value="">Select Project</option>';
        
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = project.name;
            select.appendChild(option);
        });
        
        // If there's only one project, select it automatically
        if (projects.length === 1) {
            select.value = projects[0].id;
            currentProject = projects[0].id;
            loadCurrentTabData();
        }
        
        select.addEventListener('change', (e) => {
            currentProject = e.target.value;
            console.log('Project selected:', currentProject);
            if (currentProject) {
                loadCurrentTabData();
            }
        });
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

// Load data for current tab
function loadCurrentTabData() {
    const activeTabBtn = document.querySelector('.tab-button.active');
    if (!activeTabBtn) {
        console.error('No active tab found!');
        return;
    }
    
    const activeTab = activeTabBtn.dataset.tab;
    console.log(`Loading data for active tab: ${activeTab}`);
    
    if (activeTab === 'team') {
        loadTeamData();
    } else if (activeTab === 'tasks') {
        loadTasksData();
    } else if (activeTab === 'matrix') {
        loadMatrixData();
    }
}

// Load team data
async function loadTeamData(isRefresh = false) {
    if (!currentProject) {
        console.log('No project selected for team data');
        return;
    }
    
    try {
        console.log('Loading team data for project:', currentProject);
        
        // Load team hierarchy for display and member extraction
        const hierarchyResponse = await fetch(`/api/team-hierarchy/${currentProject}`);
        const newHierarchy = await hierarchyResponse.json();
        console.log('Team hierarchy loaded for display');
        
        // Extract all members from the hierarchical structure
        members = [];
        
        // Recursive function to extract all members from the hierarchy
        function extractAllMembersFromHierarchy(items) {
            if (!items || !items.length) return;
            
            items.forEach(member => {
                if (member && member.id) {
                    members.push(member);
                    console.log("Added member from hierarchy:", member.id, `(${member.name})`);
                    
                    // Process direct reports recursively
                    if (member.direct_reports && member.direct_reports.length) {
                        extractAllMembersFromHierarchy(member.direct_reports);
                    }
                }
            });
        }
        
        // Extract members from the hierarchy
        extractAllMembersFromHierarchy(newHierarchy);
        
        // Make sure we have unique members only (in case there are duplicates)
        members = [...new Map(members.map(m => [m.id, m])).values()];
        console.log(`Loaded ${members.length} members for assignee selection`);
        
        // Debug: Print available members
        members.forEach(m => {
            console.log(`Available member: ${m.id} (${m.name})`);
        });
        
        // Debug: Get available members for task assignment
        const memberNames = members.map(m => `${m.id} (${m.name})`).join(', ');
        console.log(`Available members for assignment: ${memberNames}`);
        
        // Render the hierarchy
        const container = document.getElementById('team-hierarchy');
        if (!container) {
            console.error('Team hierarchy container not found!');
            return;
        }
        
        // Apply active view mode if available (so we keep the user's selection)
        try {
            const activeBtn = document.querySelector('.mode-btn.active');
            if (activeBtn && activeBtn.dataset.mode) {
                currentViewMode = activeBtn.dataset.mode;
                console.log("Using selected view mode for rendering:", currentViewMode);
            }
        } catch (e) {
            console.error("Could not detect active view mode:", e);
        }
        
        // Render team hierarchy
        const renderedHtml = renderTeamHierarchy(newHierarchy);
        container.innerHTML = renderedHtml;
        
        // IMPORTANT: Apply view mode class directly to the container - this is critical
        container.className = `team-hierarchy view-${currentViewMode}`;
        console.log(`Applied view mode class to container: view-${currentViewMode}`);
        
        // Setup member card interactivity
        setupMemberCards();
        
        console.log("Final members count:", members.length, "after loading team data");
    } catch (error) {
        console.error('Error loading team data:', error);
    }
}

// Render team hierarchy - completely rebuilt to avoid sub-team-group divs
function renderTeamHierarchy(hierarchy) {
    if (!hierarchy || !Array.isArray(hierarchy) || hierarchy.length === 0) {
        return '<div class="empty-state">No team members found for this project.</div>';
    }
    
    // Make currentViewMode globally accessible
    window.currentViewMode = currentViewMode;
    
    console.log("Rendering team hierarchy with view mode:", currentViewMode);
    
    // Get the currently selected view mode from the active button
    try {
        const activeBtn = document.querySelector('.mode-btn.active');
        if (activeBtn && activeBtn.dataset.mode) {
            currentViewMode = activeBtn.dataset.mode;
            console.log("Using view mode from UI:", currentViewMode);
        }
    } catch (e) {
        console.log("Error getting view mode from UI:", e);
    }
    
    let html = '';
    
    if (currentViewMode === 'pyramid') {
        // Pyramid view - preserves hierarchy but NO sub-team-group divs!
        hierarchy.forEach(member => {
            html += renderPyramidMember(member, 0);
        });
    } else {
        // For list and tile views, we completely flatten the hierarchy
        let allMembers = extractAllMembersFlat(hierarchy);
        console.log(`Extracted ${allMembers.length} members for flat view`);
        
        // Render based on view mode
        if (currentViewMode === 'list') {
            allMembers.forEach(member => {
                html += renderMemberListItem(member);
            });
        } else if (currentViewMode === 'tile') {
            allMembers.forEach(member => {
                html += renderMemberTile(member);
            });
        }
    }
    
    return html;
}

// Extract all members as a flat array - used for list and tile views
function extractAllMembersFlat(hierarchy) {
    let allMembers = [];
    
    function extract(items) {
        if (!items || !items.length) return;
        
        items.forEach(member => {
            if (member && member.id) {
                allMembers.push(member);
                
                // Process direct reports recursively
                if (member.direct_reports && member.direct_reports.length) {
                    extract(member.direct_reports);
                }
            }
        });
    }
    
    extract(hierarchy);
    return allMembers;
}

// Render a member in pyramid view - with proper nesting but NO sub-team-group divs
function renderPyramidMember(member, level) {
    if (!member) return '';
    
    let html = '';
    
    // Render this member's card
    html += `
        <div class="member-card" data-member-id="${member.id}" onclick="showMemberDetails('${member.id}')">
            <div class="member-photo">
                ${member.profile_image_path 
                    ? `<img src="${member.profile_image_path}" alt="${member.name}">` 
                    : member.name.charAt(0)
                }
            </div>
            <div class="member-info">
                <div class="member-name">${member.name}</div>
                <div class="role-badge">${member.role}</div>
                <div class="task-count">Tasks: ${member.task_count || 0}</div>
            </div>
        </div>
    `;
    
    // Process direct reports if any
    if (member.direct_reports && member.direct_reports.length > 0) {
        html += '<div class="direct-reports">';
        
        member.direct_reports.forEach(report => {
            html += renderPyramidMember(report, level + 1);
        });
        
        html += '</div>';
    }
    
    return html;
}

// Render a member in list view (single row per member)
function renderMemberListItem(member) {
    const todoCount = member.todo_count || 0;
    const readyCount = member.ready_count || 0;
    const doingCount = member.doing_count || 0;
    const testingCount = member.testing_count || 0;
    const taskCount = member.task_count || 0;
    
    // Get recent task buttons (1-2 most recent tasks)
    let recentTaskButtons = '';
    const taskElements = [];
    
    // Use recent_tasks if available (real data from API)
    if (member.recent_tasks && member.recent_tasks.length > 0) {
        // Sort by status and get most important tasks first
        const sortedTasks = [...member.recent_tasks].sort((a, b) => {
            const statusOrder = { 'DOING': 0, 'TESTING': 1, 'READY': 2, 'TODO': 3 };
            return (statusOrder[a.status] || 4) - (statusOrder[b.status] || 4);
        });
        
        // Map to expected format
        taskElements.push(...sortedTasks.slice(0, 2).map(task => ({
            id: task.id,
            title: task.title,
            type: task.status.toLowerCase()
        })));
    }
    // Otherwise try task IDs if available
    else if (member.doing_task_ids?.length > 0 || member.testing_task_ids?.length > 0 || 
             member.ready_task_ids?.length > 0 || member.todo_task_ids?.length > 0) {
        // Collect tasks in priority order (doing, testing, ready, todo)
        if (member.doing_task_ids?.length > 0) {
            taskElements.push(...member.doing_task_ids.slice(0, 2).map(id => ({id, type: 'doing'})));
        }
        if (taskElements.length < 2 && member.testing_task_ids?.length > 0) {
            taskElements.push(...member.testing_task_ids.slice(0, 2).map(id => ({id, type: 'testing'})));
        }
        if (taskElements.length < 2 && member.ready_task_ids?.length > 0) {
            taskElements.push(...member.ready_task_ids.slice(0, 2).map(id => ({id, type: 'ready'})));
        }
        if (taskElements.length < 2 && member.todo_task_ids?.length > 0) {
            taskElements.push(...member.todo_task_ids.slice(0, 2).map(id => ({id, type: 'todo'})));
        }
    }
    
    // Get the most recent 1-2 tasks
    const displayedTasks = taskElements.slice(0, 2);
    if (displayedTasks.length > 0) {
        recentTaskButtons = `
            <div class="recent-task-buttons">
                ${displayedTasks.map(({id, type, title}) => 
                    `<button class="task-btn ${type}" onclick="event.stopPropagation(); showTaskDetails('${id}')">${id}</button>`
                ).join('')}
            </div>
        `;
    }
    
    return `
        <div class="member-list-item" data-member-id="${member.id}" onclick="showMemberDetails('${member.id}')">
            <div class="member-photo">
                ${member.profile_image_path 
                    ? `<img src="${member.profile_image_path}" alt="${member.name}">` 
                    : member.name.charAt(0)
                }
            </div>
            <div class="member-name">${member.name}</div>
            <div class="role-badge">${member.role}</div>
            <div class="task-stats">
                <span class="todo-count">TODO: ${todoCount}</span>
                <span class="ready-count">READY: ${readyCount}</span>
                <span class="doing-count">DOING: ${doingCount}</span>
                <span class="testing-count">TESTING: ${testingCount}</span>
                <span class="task-count">ALL: ${taskCount}</span>
                ${recentTaskButtons}
            </div>
        </div>
    `;
}

// Render a member in tile view (card in grid)
function renderMemberTile(member) {
    const todoCount = member.todo_count || 0;
    const readyCount = member.ready_count || 0;
    const doingCount = member.doing_count || 0;
    const testingCount = member.testing_count || 0;
    const taskCount = member.task_count || 0;
    
    // Function to get task details either from tasks array or create default
    function getTaskDetails(taskId) {
        const task = tasks.find(t => t.id === taskId);
        return task ? { id: task.id, title: task.title, status: task.status } : { id: taskId, title: taskId, status: 'unknown' };
    }
    
    // Create task buttons HTML with names
    let taskButtonsHTML = '';
    const taskElements = [];
    
    // Use recent_tasks if available (real data from API)
    if (member.recent_tasks && member.recent_tasks.length > 0) {
        // Sort by status and get most important tasks first
        const sortedTasks = [...member.recent_tasks].sort((a, b) => {
            const statusOrder = { 'DOING': 0, 'TESTING': 1, 'READY': 2, 'TODO': 3 };
            return (statusOrder[a.status] || 4) - (statusOrder[b.status] || 4);
        });
        
        // Map to expected format
        taskElements.push(...sortedTasks.slice(0, 3).map(task => ({
            id: task.id,
            title: task.title,
            type: task.status.toLowerCase()
        })));
    }
    // Otherwise try task IDs if available
    else if (member.doing_task_ids?.length > 0 || member.testing_task_ids?.length > 0 || 
             member.ready_task_ids?.length > 0 || member.todo_task_ids?.length > 0) {
        // Collect tasks in priority order (doing, testing, ready, todo)
        if (member.doing_task_ids?.length > 0) {
            // Get task details for each ID
            const tasks = member.doing_task_ids.slice(0, 3).map(id => {
                const details = getTaskDetails(id);
                return { id, type: 'doing', title: details.title || id };
            });
            taskElements.push(...tasks);
        }
        
        if (taskElements.length < 3 && member.testing_task_ids?.length > 0) {
            const tasks = member.testing_task_ids.slice(0, 3 - taskElements.length).map(id => {
                const details = getTaskDetails(id);
                return { id, type: 'testing', title: details.title || id };
            });
            taskElements.push(...tasks);
        }
        
        if (taskElements.length < 3 && member.ready_task_ids?.length > 0) {
            const tasks = member.ready_task_ids.slice(0, 3 - taskElements.length).map(id => {
                const details = getTaskDetails(id);
                return { id, type: 'ready', title: details.title || id };
            });
            taskElements.push(...tasks);
        }
        
        if (taskElements.length < 3 && member.todo_task_ids?.length > 0) {
            const tasks = member.todo_task_ids.slice(0, 3 - taskElements.length).map(id => {
                const details = getTaskDetails(id);
                return { id, type: 'todo', title: details.title || id };
            });
            taskElements.push(...tasks);
        }
    }
    }
    
    // Take up to 3 most active tasks 
    const displayedTasks = taskElements.slice(0, 3);
    
    if (displayedTasks.length > 0) {
        taskButtonsHTML = `
            <div class="tile-task-buttons">
                ${displayedTasks.map(({id, type, title}) => {
                    // Get task details - either from the passed title or by looking up
                    const taskDetail = title ? { id, title } : getTaskDetails(id);
                    const truncatedTitle = taskDetail.title && taskDetail.title.length > 20 ? 
                        taskDetail.title.substring(0, 17) + '...' : 
                        (taskDetail.title || id);
                    return `
                        <div class="task-item">
                            <button class="task-btn ${type}" onclick="event.stopPropagation(); showTaskDetails('${id}')">${id}</button>
                            <span class="task-name" onclick="event.stopPropagation(); showTaskDetails('${id}')">${truncatedTitle}</span>
                        </div>
                    `;
                }).join('')}
                ${taskCount > displayedTasks.length ? `<span class="more-tasks">+${taskCount - displayedTasks.length} more</span>` : ''}
            </div>
        `;
    } else {
        taskButtonsHTML = '<div class="tile-task-buttons"><span class="no-tasks">No tasks assigned</span></div>';
    }
    
    return `
        <div class="member-tile" data-member-id="${member.id}" onclick="showMemberDetails('${member.id}')">
            <div class="member-photo">
                ${member.profile_image_path 
                    ? `<img src="${member.profile_image_path}" alt="${member.name}">` 
                    : member.name.charAt(0)
                }
            </div>
            <div class="member-name">${member.name}</div>
            <div class="role-badge">${member.role}</div>
            <div class="task-stats">
                <span class="todo-count">TODO: ${todoCount}</span>
                <span class="ready-count">READY: ${readyCount}</span>
                <span class="doing-count">DOING: ${doingCount}</span>
                <span class="testing-count">TESTING: ${testingCount}</span>
                <span class="task-count">ALL: ${taskCount}</span>
            </div>
            ${taskButtonsHTML}
        </div>
    `;
}

// Setup member cards interaction
function setupMemberCards() {
    // Set up click handlers for all member elements (cards, list items, and tiles)
    document.querySelectorAll('.member-card, .member-list-item, .member-tile').forEach(element => {
        element.addEventListener('click', () => {
            const memberId = element.dataset.memberId;
            if (memberId) {
                showMemberDetails(memberId);
            } else {
                console.error('Member ID not found on clicked element', element);
            }
        });
    });
    console.log('Added click handlers to all member elements');
}

// Load tasks data
async function loadTasksData(isRefresh = false) {
    try {
        console.log('Loading tasks data. Current project:', currentProject);
        
        let requestUrl = '/api/tasks';
        if (currentProject) {
            requestUrl += `?project_id=${currentProject}`;
        }
        
        console.log(`Fetching tasks from: ${requestUrl}`);
        const response = await fetch(requestUrl);
        const newTasks = await response.json();
        console.log(`Loaded ${newTasks.length} tasks:`, newTasks);
        
        // Update tasks and render
        tasks = newTasks;
        renderTasks(tasks);
        
        // Update assignee filter if needed
        updateAssigneeFilter();
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

// Render tasks
function renderTasks(taskList) {
    const container = document.getElementById('tasks-list');
    if (!container) {
        console.error('Tasks list container not found!');
        return;
    }
    
    if (!taskList || taskList.length === 0) {
        container.innerHTML = '<div class="empty-state">No tasks found.</div>';
        return;
    }
    
    container.innerHTML = `
        <table class="task-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Assignee</th>
                    <th>Priority</th>
                </tr>
            </thead>
            <tbody>
                ${taskList.map(task => `
                    <tr class="task-row" data-task-id="${task.id}" onclick="showTaskDetails('${task.id}')">
                        <td class="task-id">${task.id}</td>
                        <td class="task-title">${task.title}</td>
                        <td><span class="task-status ${task.status.toLowerCase()}">${task.status}</span></td>
                        <td>${task.assignee || '-'}</td>
                        <td>${task.priority || '-'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Update assignee filter
function updateAssigneeFilter() {
    const select = document.getElementById('assignee-filter');
    if (!select) return;
    
    const currentValue = select.value;
    select.innerHTML = '<option value="">All</option>';
    
    // Add unique assignees from tasks
    const assignees = [...new Set(tasks.filter(t => t.assignee).map(t => t.assignee))];
    assignees.forEach(assignee => {
        const option = document.createElement('option');
        option.value = assignee;
        option.textContent = assignee;
        select.appendChild(option);
    });
    
    // Restore selection if possible
    if (currentValue && assignees.includes(currentValue)) {
        select.value = currentValue;
    }
}

// Load matrix data
async function loadMatrixData(isRefresh = false) {
    try {
        console.log('Loading matrix data. Current project:', currentProject);
        
        let requestUrl = '/api/traceability-matrix';
        if (currentProject) {
            requestUrl += `?project_id=${currentProject}`;
        }
        
        console.log(`Fetching matrix from: ${requestUrl}`);
        const response = await fetch(requestUrl);
        const matrixData = await response.json();
        console.log('Matrix data:', matrixData);
        
        renderMatrix(matrixData);
    } catch (error) {
        console.error('Error loading matrix data:', error);
    }
}

// Render traceability matrix
function renderMatrix(data) {
    const container = document.getElementById('matrix-container');
    if (!container) {
        console.error('Matrix container not found!');
        return;
    }
    
    if (!data || !data.tasks || data.tasks.length === 0 || !data.files || data.files.length === 0) {
        container.innerHTML = '<div class="empty-state">No data available for traceability matrix.</div>';
        return;
    }
    
    let html = '<table class="matrix-table"><thead><tr><th>Task / File</th>';
    
    // Header row with file names
    data.files.forEach(file => {
        const fileName = file.split('/').pop();
        html += `<th title="${file}">${fileName}</th>`;
    });
    
    html += '</tr></thead><tbody>';
    
    // Task rows
    data.tasks.forEach((task, taskIndex) => {
        html += `<tr>
            <th onclick="showTaskDetails('${task.id}')" class="clickable-task" title="Click to view task details">
                ${task.title}
            </th>`;
        
        // For each file, show relationship
        data.matrix[taskIndex].forEach((hasRelation, fileIndex) => {
            html += `<td class="matrix-cell ${hasRelation ? 'has-relation' : ''}">${hasRelation ? '●' : ''}</td>`;
        });
        
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Show member details
function showMemberDetails(memberId) {
    const member = members.find(m => m.id === memberId);
    if (!member) {
        console.error(`Member not found: ${memberId}`);
        return;
    }
    
    const modal = document.getElementById('member-modal');
    const content = document.getElementById('member-details');
    
    content.innerHTML = `
        <h2>${member.name}</h2>
        <div class="member-photo large">
            ${member.profile_image_path 
                ? `<img src="${member.profile_image_path}" alt="${member.name}">` 
                : member.name.charAt(0)
            }
        </div>
        <div class="member-detail-section">
            <p><strong>Role:</strong> ${member.role}</p>
            <p><strong>Position:</strong> ${member.position}</p>
            <p><strong>Task Count:</strong> ${member.task_count || 0}</p>
            <p><strong>Profile:</strong> ${member.profile || 'Not available'}</p>
        </div>
        
        <div class="member-detail-section">
            <h3>Tasks</h3>
            ${member.recent_tasks && member.recent_tasks.length > 0 
                ? `<ul class="recent-tasks-list">
                    ${member.recent_tasks.map(task => `
                        <li>
                            <span class="task-status ${task.status.toLowerCase()}">${task.status}</span>
                            <span class="task-title" onclick="showTaskDetails('${task.id}')">${task.title}</span>
                        </li>
                    `).join('')}
                  </ul>`
                : '<p>No tasks assigned</p>'
            }
        </div>
    `;
    
    modal.style.display = 'block';
}

// Show task details
function showTaskDetails(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) {
        console.error(`Task not found: ${taskId}`);
        return;
    }
    
    const modal = document.getElementById('task-modal');
    const content = document.getElementById('task-details');
    
    // Get member names for assignee dropdown
    const memberOptions = members.map(m => 
        `<option value="${m.id}" ${m.id === task.assignee ? 'selected' : ''}>${m.name}</option>`
    ).join('');
    
    content.innerHTML = `
        <h2>${task.title}</h2>
        <div class="detail-section">
            <h3>Basic Information</h3>
            <p><strong>ID:</strong> ${task.id}</p>
            <p>
                <strong>Status:</strong> 
                <select id="task-status-select" class="task-status-select" onchange="updateTaskStatus('${task.id}', this.value)">
                    <option value="TODO" ${task.status === 'TODO' ? 'selected' : ''}>TODO</option>
                    <option value="READY" ${task.status === 'READY' ? 'selected' : ''}>READY</option>
                    <option value="DOING" ${task.status === 'DOING' ? 'selected' : ''}>DOING</option>
                    <option value="TESTING" ${task.status === 'TESTING' ? 'selected' : ''}>TESTING</option>
                    <option value="DONE" ${task.status === 'DONE' ? 'selected' : ''}>DONE</option>
                </select>
            </p>
            <p>
                <strong>Assignee:</strong> 
                <select id="task-assignee-select" class="task-assignee-select" onchange="updateTaskAssignee('${task.id}', this.value)">
                    <option value="">Unassigned</option>
                    ${memberOptions}
                </select>
            </p>
            <p><strong>Priority:</strong> ${task.priority || 'Not set'}</p>
            <p><strong>Description:</strong> ${task.description || 'No description'}</p>
        </div>
        
        <div class="detail-section">
            <h3>Related Files</h3>
            ${task.files && task.files.length > 0 
                ? `<ul class="file-list">
                    ${task.files.map(f => `<li>${f.file_path}</li>`).join('')}
                  </ul>`
                : '<p>No files associated</p>'
            }
        </div>
    `;
    
    modal.style.display = 'block';
}

// Update task status
async function updateTaskStatus(taskId, newStatus) {
    console.log(`Updating task ${taskId} status to ${newStatus}`);
    
    try {
        const response = await fetch(`/api/tasks/${taskId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            // Handle error response
            const errorData = await response.json();
            console.error('Error updating task status:', errorData);
            alert(`Failed to update status: ${errorData.detail || 'Unknown error'}`);
            return;
        }
        
        // Parse response
        const data = await response.json();
        console.log('Task status updated:', data);
        
        // Update local task
        const task = tasks.find(t => t.id === taskId);
        if (task) {
            task.status = newStatus;
            
            // Refresh task list
            renderTasks(tasks);
            
            // Show success indicator
            showUpdateIndicator(`Task ${taskId} status updated to ${newStatus}`);
        }
    } catch (error) {
        console.error('Error updating task status:', error);
        alert(`Failed to update status: ${error.message}`);
    }
}

// Update task assignee
async function updateTaskAssignee(taskId, newAssignee) {
    console.log(`Updating task ${taskId} assignee to ${newAssignee}`);
    
    try {
        const response = await fetch(`/api/tasks/${taskId}/assignee`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ assignee: newAssignee })
        });
        
        if (!response.ok) {
            // Handle error response
            const errorData = await response.json();
            console.error('Error updating task assignee:', errorData);
            alert(`Failed to update assignee: ${errorData.detail || 'Unknown error'}`);
            return;
        }
        
        // Parse response
        const data = await response.json();
        console.log('Task assignee updated:', data);
        
        // Update local task
        const task = tasks.find(t => t.id === taskId);
        if (task) {
            task.assignee = newAssignee;
            
            // Refresh task list
            renderTasks(tasks);
            
            // Get assignee name
            const assigneeName = newAssignee ? 
                (members.find(m => m.id === newAssignee)?.name || newAssignee) : 
                'Unassigned';
            
            // Show success indicator
            showUpdateIndicator(`Task ${taskId} assigned to ${assigneeName}`);
        }
    } catch (error) {
        console.error('Error updating task assignee:', error);
        alert(`Failed to update assignee: ${error.message}`);
    }
}

// Setup auto refresh
function setupAutoRefresh() {
    autoRefreshInterval = setInterval(() => {
        if (isAutoRefreshEnabled && currentProject) {
            console.log('Auto-refreshing data...');
            loadCurrentTabData();
        }
    }, REFRESH_INTERVAL);
}

// Make key functions available globally at the end of the file
// This must be at the end after all functions are defined
document.addEventListener('DOMContentLoaded', () => {
    window.loadTeamData = loadTeamData;
    window.changeViewMode = changeViewMode;
    window.showMemberDetails = showMemberDetails;
    window.showTaskDetails = showTaskDetails;
    window.updateTaskStatus = updateTaskStatus;
    window.updateTaskAssignee = updateTaskAssignee;
});