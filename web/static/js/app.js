// Global variables - VERSION 3.0 (IMPROVED FOR LIST AND TILE VIEWS)
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
let taskViewMode = localStorage.getItem('taskViewMode') || 'table'; // Task view mode: table or hierarchy
let userTimezone = localStorage.getItem('userTimezone') || Intl.DateTimeFormat().resolvedOptions().timeZone; // User's selected timezone
let matrixDataLoaded = false; // Track if matrix has been loaded at least once

// Format date with timezone
function formatDateWithTimezone(dateStr, includeTime = true) {
    if (!dateStr) return '-';
    try {
        // Handle different date string formats
        let date;
        
        // Parse the date string
        // Check if it looks like an ISO string without timezone (YYYY-MM-DDTHH:MM:SS)
        if (dateStr.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/) || 
            dateStr.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
            // Add Z to indicate UTC
            date = new Date(dateStr.replace(' ', 'T') + 'Z');
        } else {
            date = new Date(dateStr);
        }
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            console.error('Invalid date:', dateStr);
            return dateStr;
        }
        
        const options = {
            timeZone: userTimezone,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            ...(includeTime && {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            })
        };
        
        // Format the date in the selected timezone
        const formatted = new Intl.DateTimeFormat('en-US', options).format(date);
        
        // Add timezone abbreviation for clarity
        const timeZoneAbbr = getTimezoneAbbreviation(userTimezone);
        return includeTime ? `${formatted} ${timeZoneAbbr}` : formatted;
        
    } catch (e) {
        console.error('Error formatting date:', e);
        return dateStr;
    }
}

// Get timezone abbreviation for display
function getTimezoneAbbreviation(timezone) {
    const abbreviations = {
        'UTC': 'UTC',
        'America/New_York': 'EST/EDT',
        'America/Chicago': 'CST/CDT',
        'America/Denver': 'MST/MDT',
        'America/Los_Angeles': 'PST/PDT',
        'Europe/London': 'GMT/BST',
        'Europe/Paris': 'CET/CEST',
        'Europe/Berlin': 'CET/CEST',
        'Asia/Tokyo': 'JST',
        'Asia/Shanghai': 'CST',
        'Asia/Singapore': 'SGT',
        'Asia/Dubai': 'GST',
        'Australia/Sydney': 'AEST/AEDT',
        'Pacific/Auckland': 'NZST/NZDT'
    };
    return abbreviations[timezone] || timezone;
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('TracLine Web Interface initializing...');
    
    try {
        // Load projects first
        loadProjects();
        setupTabs();
        setupModals();
        setupFilters();
        setupAutoRefresh();
        setupTaskViewSwitcher();
        setupLogsControls();  // Add this to fix logs controls
        setupTimezoneSettings(); // Add timezone settings initialization
        
        // Debug information
        console.log('DOM elements:');
        console.log('- project-select:', document.getElementById('project-select'));
        console.log('- team-hierarchy:', document.getElementById('team-hierarchy'));
        console.log('- tasks-list:', document.getElementById('tasks-list'));
        console.log('- matrix-container:', document.getElementById('matrix-container'));
        
        // Wait for project selection before loading data
        // This ensures Task Dashboard and Matrix are properly filtered
    } catch (error) {
        console.error('Error during initialization:', error);
        console.error('Stack trace:', error.stack);
    }
});

// Show update indicator
function showUpdateIndicator(message) {
    // Remove any existing indicators
    const existingIndicator = document.querySelector('.refresh-indicator');
    if (existingIndicator) {
        existingIndicator.remove();
    }
    
    const indicator = document.createElement('div');
    indicator.className = 'refresh-indicator';
    indicator.textContent = message;
    document.body.appendChild(indicator);
    
    // Add timestamp for debugging
    console.log(`[UPDATE] ${message} at ${new Date().toLocaleTimeString()}`);
    
    setTimeout(() => {
        indicator.remove();
    }, 3000);
}

// Show message when no project is selected
function showNoProjectMessage(tabName) {
    let container;
    let message = 'Please select a project to view data.';
    
    if (tabName === 'tasks') {
        container = document.getElementById('tasks-list');
    } else if (tabName === 'team') {
        container = document.getElementById('team-hierarchy');
    } else if (tabName === 'matrix') {
        container = document.getElementById('matrix-container');
    }
    
    if (container) {
        container.innerHTML = `<div class="empty-state">${message}</div>`;
    }
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
            if (currentProject) {
                // All tabs need a project selected
                if (tabName === 'tasks') {
                    loadTasksData();
                } else if (tabName === 'team') {
                    loadTeamData();
                } else if (tabName === 'logs') {
                    console.log('🔍 [TAB DEBUG] Logs tab clicked, calling loadLogsData()');
                    loadLogsData();
                } else if (tabName === 'matrix') {
                    // Don't load data automatically - show instruction instead
                    showMatrixInstruction();
                    setupMatrixFilters();
                }
            } else {
                // Show message if no project selected
                showNoProjectMessage(tabName);
            }
            
            if (tabName === 'settings') {
                loadSettings();
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
        const savedCurrentProject = projectData.current_project || null;
        console.log('Loaded projects:', projects);
        console.log('Current project from backend:', savedCurrentProject);
        
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
        
        // Select the current project from backend, or the first one if only one exists
        if (savedCurrentProject && projects.some(p => p.id === savedCurrentProject)) {
            select.value = savedCurrentProject;
            currentProject = savedCurrentProject;
            loadCurrentTabData();
        } else if (projects.length === 1) {
            select.value = projects[0].id;
            currentProject = projects[0].id;
            loadCurrentTabData();
        }
        
        select.addEventListener('change', (e) => {
            currentProject = e.target.value;
            console.log('Project selected:', currentProject);
            
            // Reset matrix loaded flag when project changes
            matrixDataLoaded = false;
            
            if (currentProject) {
                loadCurrentTabData();
            }
        });
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

// Load data for current tab
async function loadCurrentTabData() {
    const activeTabBtn = document.querySelector('.tab-button.active');
    if (!activeTabBtn) {
        console.error('No active tab found!');
        return;
    }
    
    const activeTab = activeTabBtn.dataset.tab;
    console.log(`[REFRESH] Loading data for active tab: ${activeTab}`);
    
    // Only load data if a project is selected
    if (!currentProject) {
        console.log('No project selected, skipping data load');
        showNoProjectMessage(activeTab);
        return;
    }
    
    try {
        // Load tasks data for the selected project
        await loadTasksData();
        
        if (activeTab === 'team') {
            await loadTeamData();
        } else if (activeTab === 'tasks') {
            // Tasks are already loaded above
            console.log('[REFRESH] Tasks tab data refreshed');
        } else if (activeTab === 'matrix') {
            // Only refresh matrix if it has been loaded before
            if (matrixDataLoaded) {
                await loadMatrixData(true); // isRefresh = true
            }
        }
        
        console.log(`[REFRESH] Completed refresh for ${activeTab} tab`);
    } catch (error) {
        console.error('[REFRESH] Error during auto-refresh:', error);
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
        console.log('[TEAM DATA DEBUG] Full hierarchy response:', newHierarchy);
        
        // Debug: Check AI-TARGE in the hierarchy
        function findAITarge(items) {
            if (!items || !items.length) return;
            items.forEach(member => {
                if (member.id === 'AI-TARGE' || member.name === 'AI-TARGE') {
                    console.log('[TEAM DATA DEBUG] Found AI-TARGE in hierarchy:', member);
                    console.log('[TEAM DATA DEBUG] AI-TARGE task_count from API:', member.task_count);
                }
                if (member.direct_reports) {
                    findAITarge(member.direct_reports);
                }
            });
        }
        findAITarge(newHierarchy);
        
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
        // Pyramid view - now uses hierarchical card layout (org chart style)
        html = renderOrganizationChart(hierarchy);
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
                
                // Debug logging for AI-TARGE during extraction
                if (member.id === 'AI-TARGE' || member.name === 'AI-TARGE') {
                    console.log('[EXTRACT DEBUG] AI-TARGE member during extraction:', member);
                    console.log('[EXTRACT DEBUG] AI-TARGE task_count during extraction:', member.task_count);
                }
                
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
    
    // Get recent task buttons for pyramid view
    let taskButtonsHTML = '';
    const taskElements = [];
    
    // Use recent_tasks if available (real data from API)
    if (member.recent_tasks && member.recent_tasks.length > 0) {
        // Debug log for DOING tasks
        const doingTasks = member.recent_tasks.filter(t => t.status === 'DOING');
        if (doingTasks.length > 0) {
            console.log(`[PYRAMID] ${member.name} has ${doingTasks.length} DOING tasks:`, doingTasks);
        }
        
        // recent_tasks are already sorted by backend (DOING first), so use them directly
        // No need to re-sort here as backend already orders by status priority
        
        // Debug log tasks from backend
        console.log(`[PYRAMID] ${member.name} recent_tasks from backend:`, member.recent_tasks.map(t => ({id: t.id, status: t.status})));
        
        // Map to expected format - show only 1 task for pyramid view
        taskElements.push(...member.recent_tasks.slice(0, 1).map(task => {
            const taskElement = {
                id: task.id,
                title: task.title,
                type: task.status.toLowerCase()
            };
            // Debug log the conversion
            console.log(`[PYRAMID] Converting task ${task.id}: status="${task.status}" -> type="${taskElement.type}"`);
            return taskElement;
        }));
    }
    // Otherwise try task IDs if available
    else if (member.doing_task_ids?.length > 0 || member.testing_task_ids?.length > 0 || 
             member.ready_task_ids?.length > 0 || member.todo_task_ids?.length > 0) {
        // Collect only 1 task in priority order for pyramid view
        const allTaskIds = [
            ...(member.doing_task_ids || []).map(id => ({id, type: 'doing'})),
            ...(member.testing_task_ids || []).map(id => ({id, type: 'testing'})),
            ...(member.ready_task_ids || []).map(id => ({id, type: 'ready'})),
            ...(member.todo_task_ids || []).map(id => ({id, type: 'todo'})),
            ...(member.pending_task_ids || []).map(id => ({id, type: 'pending'}))
        ];
        taskElements.push(...allTaskIds.slice(0, 1));
    }
    
    // Get only 1 recent task for pyramid view
    const displayedTasks = taskElements.slice(0, 1);
    if (displayedTasks.length > 0) {
        taskButtonsHTML = `
            <div class="pyramid-task-buttons">
                ${displayedTasks.map(({id, type, title}) => {
                    const truncatedTitle = title && title.length > 12 ? 
                        title.substring(0, 9) + '...' : 
                        (title || id);
                    // Debug log task type
                    if (type === 'doing') {
                        console.log(`[PYRAMID BUTTON] Creating DOING button for ${id} with type="${type}"`);
                    }
                    return `
                        <div class="pyramid-task-item">
                            <button class="task-btn ${type}" onclick="event.stopPropagation(); showTaskDetails('${id}')">${id}</button>
                            <span class="task-name" onclick="event.stopPropagation(); showTaskDetails('${id}')">${truncatedTitle}</span>
                        </div>
                    `;
                }).join('')}
                ${member.task_count > displayedTasks.length ? `<div class="more-tasks">+${member.task_count - displayedTasks.length} more</div>` : ''}
            </div>
        `;
    }
    
    let html = '';
    
    // Render this member's card
    html += `
        <div class="member-card" data-member-id="${member.id}" onclick="showMemberDetails('${member.id}')">
            <div class="member-photo">
                ${member.avatar_url || member.profile_image_path 
                    ? `<img src="${member.avatar_url || member.profile_image_path}?t=${Date.now()}" alt="${member.name}">` 
                    : member.name.charAt(0)
                }
            </div>
            <div class="member-info">
                <div class="member-name">${member.name}</div>
                <div class="role-badge">${member.role}</div>
                <div class="task-count">Tasks: ${member.task_count || 0}</div>
                ${taskButtonsHTML}
            </div>
        </div>
    `;
    
    // Process direct reports if any (no wrapper div needed)
    if (member.direct_reports && member.direct_reports.length > 0) {
        member.direct_reports.forEach(report => {
            html += renderPyramidMember(report, level + 1);
        });
    }
    
    return html;
}

// Render a member in list view (single row per member)
function renderMemberListItem(member) {
    // Calculate status counts from recent_tasks if available
    let todoCount = 0, readyCount = 0, doingCount = 0, testingCount = 0;
    
    if (member.recent_tasks && Array.isArray(member.recent_tasks)) {
        member.recent_tasks.forEach(task => {
            switch(task.status) {
                case 'TODO': todoCount++; break;
                case 'READY': readyCount++; break;
                case 'DOING': doingCount++; break;
                case 'TESTING': testingCount++; break;
            }
        });
    }
    
    // Use member properties if available, otherwise use calculated values
    todoCount = member.todo_count !== undefined ? member.todo_count : todoCount;
    readyCount = member.ready_count !== undefined ? member.ready_count : readyCount;
    doingCount = member.doing_count !== undefined ? member.doing_count : doingCount;
    testingCount = member.testing_count !== undefined ? member.testing_count : testingCount;
    const taskCount = member.task_count || 0;
    
    // Debug logging for AI-TARGE
    if (member.id === 'AI-TARGE' || member.name === 'AI-TARGE') {
        console.log('[LIST VIEW DEBUG] AI-TARGE member data:', member);
        console.log('[LIST VIEW DEBUG] AI-TARGE task_count:', member.task_count);
        console.log('[LIST VIEW DEBUG] AI-TARGE recent_tasks:', member.recent_tasks);
    }
    
    // Get recent task buttons (1-2 most recent tasks)
    let recentTaskButtons = '';
    const taskElements = [];
    
    // Use recent_tasks if available (real data from API)
    if (member.recent_tasks && member.recent_tasks.length > 0) {
        // Debug log for DOING tasks
        const doingTasks = member.recent_tasks.filter(t => t.status === 'DOING');
        if (doingTasks.length > 0) {
            console.log(`[LIST] ${member.name} has ${doingTasks.length} DOING tasks:`, doingTasks);
        }
        
        // Sort by status and get most important tasks first
        // recent_tasks are already sorted by backend, use them directly
        
        // Map to expected format
        taskElements.push(...member.recent_tasks.slice(0, 2).map(task => ({
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
                ${member.avatar_url || member.profile_image_path 
                    ? `<img src="${member.avatar_url || member.profile_image_path}?t=${Date.now()}" alt="${member.name}">` 
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
        // Debug log for DOING tasks
        const doingTasks = member.recent_tasks.filter(t => t.status === 'DOING');
        if (doingTasks.length > 0) {
            console.log(`[TILE] ${member.name} has ${doingTasks.length} DOING tasks:`, doingTasks);
        }
        
        // Sort by status and get most important tasks first
        // recent_tasks are already sorted by backend, use them directly
        
        // Map to expected format - tile view gets only 1 task
        taskElements.push(...member.recent_tasks.slice(0, 1).map(task => ({
            id: task.id,
            title: task.title,
            type: task.status.toLowerCase()
        })));
    }
    // Otherwise try task IDs if available
    else if (member.doing_task_ids?.length > 0 || member.testing_task_ids?.length > 0 || 
             member.ready_task_ids?.length > 0 || member.todo_task_ids?.length > 0) {
        // Collect only 1 task in priority order (doing, testing, ready, todo)
        if (member.doing_task_ids?.length > 0) {
            const details = getTaskDetails(member.doing_task_ids[0]);
            taskElements.push({ id: member.doing_task_ids[0], type: 'doing', title: details.title || member.doing_task_ids[0] });
        }
        else if (member.testing_task_ids?.length > 0) {
            const details = getTaskDetails(member.testing_task_ids[0]);
            taskElements.push({ id: member.testing_task_ids[0], type: 'testing', title: details.title || member.testing_task_ids[0] });
        }
        else if (member.ready_task_ids?.length > 0) {
            const details = getTaskDetails(member.ready_task_ids[0]);
            taskElements.push({ id: member.ready_task_ids[0], type: 'ready', title: details.title || member.ready_task_ids[0] });
        }
        else if (member.todo_task_ids?.length > 0) {
            const details = getTaskDetails(member.todo_task_ids[0]);
            taskElements.push({ id: member.todo_task_ids[0], type: 'todo', title: details.title || member.todo_task_ids[0] });
        }
    }
    
    // Take only 1 task for tile view 
    const displayedTasks = taskElements.slice(0, 1);
    
    if (displayedTasks.length > 0) {
        taskButtonsHTML = `
            <div class="tile-task-buttons">
                ${displayedTasks.map(({id, type, title}) => {
                    // Get task details - either from the passed title or by looking up
                    const taskDetail = title ? { id, title } : getTaskDetails(id);
                    const truncatedTitle = taskDetail.title && taskDetail.title.length > 15 ? 
                        taskDetail.title.substring(0, 12) + '...' : 
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
                ${member.avatar_url || member.profile_image_path 
                    ? `<img src="${member.avatar_url || member.profile_image_path}?t=${Date.now()}" alt="${member.name}">` 
                    : member.name.charAt(0)
                }
            </div>
            <div class="member-name">${member.name}</div>
            <div class="role-badge">${member.role}</div>
            <div class="task-summary">Tasks: ${taskCount}</div>
            ${taskButtonsHTML}
        </div>
    `;
}


// Render organization chart view with hierarchical tile layout
function renderOrganizationChart(hierarchy) {
    if (!hierarchy || hierarchy.length === 0) {
        return '<div class="org-chart-container"><p>No hierarchy data available</p></div>';
    }
    
    // Organize members by hierarchy level
    const ceoMembers = [];
    const executiveMembers = [];
    const teamLeaders = [];
    const seniorMembers = [];
    const regularMembers = [];
    
    function categorizeMembers(members) {
        members.forEach(member => {
            // Determine hierarchy level based on position and role
            if (member.role === 'OWNER' || member.position === 'LEADER' && !member.leader_id) {
                ceoMembers.push(member);
            } else if (member.position === 'LEADER' && member.leader_id) {
                executiveMembers.push(member);
            } else if (member.position === 'SUB_LEADER') {
                teamLeaders.push(member);
            } else {
                regularMembers.push(member);
            }
            
            // Recursively categorize direct reports
            if (member.direct_reports && member.direct_reports.length > 0) {
                categorizeMembers(member.direct_reports);
            }
        });
    }
    
    categorizeMembers(hierarchy);
    
    let html = '<div class="org-chart-container">';
    
    // CEO Level
    if (ceoMembers.length > 0) {
        html += '<div class="org-level ceo-level">';
        ceoMembers.forEach(member => {
            html += renderOrgCard(member, 'ceo');
        });
        html += '</div>';
    }
    
    // Executive Level
    if (executiveMembers.length > 0) {
        html += '<div class="org-level executives-level">';
        executiveMembers.forEach(member => {
            html += renderOrgCard(member, 'executive');
        });
        html += '</div>';
    }
    
    // Team Leaders Level with their teams
    if (teamLeaders.length > 0) {
        html += '<div class="org-level teams-level">';
        
        teamLeaders.forEach(leader => {
            html += '<div class="org-team-group">';
            
            // Render team leader
            html += renderOrgCard(leader, 'leader');
            
            // Render team members under this leader
            const teamMembers = getTeamMembers(leader.id, regularMembers);
            if (teamMembers.length > 0) {
                html += '<div class="org-team-members">';
                teamMembers.forEach(member => {
                    html += renderOrgCard(member, 'member');
                });
                html += '</div>';
            }
            
            html += '</div>';
        });
        
        html += '</div>';
    }
    
    // Independent Members (no leader)
    const independentMembers = regularMembers.filter(member => !member.leader_id);
    if (independentMembers.length > 0) {
        html += '<div class="org-level independent-level">';
        html += '<div class="org-team-group">';
        html += '<div class="org-card independent-header"><h4>Independent Contributors</h4></div>';
        html += '<div class="org-team-members">';
        independentMembers.forEach(member => {
            html += renderOrgCard(member, 'member');
        });
        html += '</div>';
        html += '</div>';
        html += '</div>';
    }
    
    html += '</div>';
    return html;
}

// Get team members for a specific leader
function getTeamMembers(leaderId, allMembers) {
    return allMembers.filter(member => member.leader_id === leaderId);
}

// Render a single organization chart card
function renderOrgCard(member, cardType) {
    const taskCount = member.task_count || 0;
    const reportsCount = member.direct_reports ? member.direct_reports.length : 0;
    
    const cardClass = `org-card ${cardType}-card`;
    
    // Build recent task buttons (up to 3)
    let taskButtonsHTML = '';
    const taskElements = [];
    
    // Function to get task details either from tasks array or create default
    function getTaskDetails(taskId) {
        const task = tasks.find(t => t.id === taskId);
        return task ? { id: task.id, title: task.title, status: task.status } : { id: taskId, title: taskId, status: 'unknown' };
    }
    
    // Use recent_tasks if available (real data from API)
    if (member.recent_tasks && member.recent_tasks.length > 0) {
        // Debug log for DOING tasks
        const doingTasks = member.recent_tasks.filter(t => t.status === 'DOING');
        if (doingTasks.length > 0) {
            console.log(`[ORG-CARD] ${member.name} has ${doingTasks.length} DOING tasks:`, doingTasks);
        }
        
        // Sort by status priority first, then by task priority
        // recent_tasks are already sorted by backend (DOING first), use them directly
        
        // Map to expected format - show only 1 task for pyramid/org view
        taskElements.push(...member.recent_tasks.slice(0, 1).map(task => ({
            id: task.id,
            title: task.title,
            type: task.status.toLowerCase()
        })));
    }
    // Otherwise try task IDs if available
    else if (member.doing_task_ids?.length > 0 || member.testing_task_ids?.length > 0 || 
             member.ready_task_ids?.length > 0 || member.todo_task_ids?.length > 0) {
        // Collect only 1 task in priority order for pyramid/org view
        const allTaskIds = [
            ...(member.doing_task_ids || []).map(id => ({id, type: 'doing'})),
            ...(member.testing_task_ids || []).map(id => ({id, type: 'testing'})),
            ...(member.ready_task_ids || []).map(id => ({id, type: 'ready'})),
            ...(member.todo_task_ids || []).map(id => ({id, type: 'todo'})),
            ...(member.pending_task_ids || []).map(id => ({id, type: 'pending'}))
        ];
        
        taskElements.push(...allTaskIds.slice(0, 1).map(taskInfo => {
            const details = getTaskDetails(taskInfo.id);
            return {
                id: taskInfo.id,
                title: details.title || taskInfo.id,
                type: taskInfo.type
            };
        }));
    }
    
    // Build task buttons HTML
    if (taskElements.length > 0) {
        taskButtonsHTML = `
            <div class="org-card-task-buttons">
                ${taskElements.map(({id, type, title}) => {
                    const truncatedTitle = title && title.length > 15 ? 
                        title.substring(0, 12) + '...' : 
                        (title || id);
                    return `
                        <div class="org-task-item">
                            <button class="task-btn ${type}" onclick="event.stopPropagation(); showTaskDetails('${id}')">${id}</button>
                            <span class="org-task-name" onclick="event.stopPropagation(); showTaskDetails('${id}')">${truncatedTitle}</span>
                        </div>
                    `;
                }).join('')}
                ${taskCount > taskElements.length ? `<div class="org-more-tasks">+${taskCount - taskElements.length} more</div>` : ''}
            </div>
        `;
    } else if (taskCount > 0) {
        taskButtonsHTML = '<div class="org-card-task-buttons"><div class="org-no-tasks">Tasks available (click to view)</div></div>';
    } else {
        taskButtonsHTML = '<div class="org-card-task-buttons"><div class="org-no-tasks">No tasks assigned</div></div>';
    }
    
    return `
        <div class="${cardClass}" data-member-id="${member.id}" onclick="showMemberDetails('${member.id}')">
            <div class="org-card-header">
                <div class="clickable-photo org-card-photo" onclick="event.stopPropagation(); openPhotoUpload('${member.id}')">
                    ${member.avatar_url || member.profile_image_path 
                        ? `<img src="${member.avatar_url || member.profile_image_path}" alt="${member.name}">` 
                        : member.name.charAt(0)
                    }
                </div>
                <div class="org-card-info">
                    <div class="org-card-name">${member.name}</div>
                    <div class="org-card-title">${member.id}</div>
                    <div class="org-card-role">${member.role} - ${member.position}</div>
                </div>
            </div>
            ${taskButtonsHTML}
            <div class="org-card-footer">
                <div class="org-task-count">${taskCount} tasks</div>
                ${reportsCount > 0 ? `<div class="org-reports-count">${reportsCount} reports</div>` : ''}
            </div>
        </div>
    `;
}

// Setup member cards interaction
function setupMemberCards() {
    // Set up click handlers for all member elements (cards, list items, tiles, and org cards)
    document.querySelectorAll('.member-card, .member-list-item, .member-tile, .org-card').forEach(element => {
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
        const params = [];
        
        // Check if we're on the Task Dashboard tab
        const activeTab = document.querySelector('.tab-button.active');
        const isTaskDashboard = activeTab && activeTab.getAttribute('data-tab') === 'tasks';
        
        // Always filter by project if a project is selected
        // This ensures both Task Dashboard and other tabs respect project selection
        if (currentProject) {
            params.push(`project_id=${currentProject}`);
        }
        
        // Get filter values
        const assigneeFilter = document.getElementById('assignee-filter');
        const statusFilter = document.getElementById('status-filter');
        const priorityFilter = document.getElementById('priority-filter');
        const nonDoneFilter = document.getElementById('non-done-filter');
        
        // Apply assignee filter
        if (assigneeFilter && assigneeFilter.value) {
            params.push(`assignee=${encodeURIComponent(assigneeFilter.value)}`);
        }
        
        // Apply status filter (multiple selection)
        if (statusFilter) {
            const selectedStatuses = Array.from(statusFilter.selectedOptions).map(opt => opt.value);
            if (selectedStatuses.length === 1) {
                // Single status selected
                params.push(`status=${encodeURIComponent(selectedStatuses[0])}`);
            } else if (selectedStatuses.length > 1) {
                // Multiple statuses - need to handle this differently
                // For now, we'll fetch all and filter client-side
                console.log('Multiple statuses selected:', selectedStatuses);
            }
        }
        
        // Apply priority filter
        if (priorityFilter && priorityFilter.value) {
            params.push(`priority=${encodeURIComponent(priorityFilter.value)}`);
        }
        
        // Build final URL
        if (params.length > 0) {
            requestUrl += '?' + params.join('&');
        }
        
        console.log(`Fetching tasks from: ${requestUrl}`);
        const response = await fetch(requestUrl);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        let newTasks = await response.json();
        console.log(`Loaded ${newTasks.length} tasks from API`);
        
        // Make sure tasks is an array
        if (!Array.isArray(newTasks)) {
            console.error('API did not return an array of tasks:', newTasks);
            newTasks = [];
        }
        
        // Client-side filtering for multiple statuses
        if (statusFilter) {
            const selectedStatuses = Array.from(statusFilter.selectedOptions).map(opt => opt.value);
            if (selectedStatuses.length > 1) {
                newTasks = newTasks.filter(task => selectedStatuses.includes(task.status));
                console.log(`Filtered to ${newTasks.length} tasks by status`);
            }
        }
        
        // Apply non-DONE filter
        if (nonDoneFilter && nonDoneFilter.checked) {
            const beforeCount = newTasks.length;
            newTasks = newTasks.filter(task => task.status !== 'DONE');
            console.log(`Filtered out DONE tasks: ${beforeCount} -> ${newTasks.length} tasks`);
        }
        
        // Update tasks and render
        tasks = newTasks;
        renderTasks(tasks);
        
        // Update assignee filter if needed
        updateAssigneeFilter();
    } catch (error) {
        console.error('Error loading tasks:', error);
        // Show error message to user
        const container = document.getElementById('tasks-list');
        if (container) {
            container.innerHTML = `<div class="error-state">Error loading tasks: ${error.message}</div>`;
        }
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
                    <th>Relations</th>
                    <th>Files</th>
                </tr>
            </thead>
            <tbody>
                ${taskList.map(task => {
                    // Debug: Log task data to see what we're getting
                    console.log('Rendering task:', task.id, 'relationships:', task.relationships, 'files:', task.files);
                    
                    // Get assignee name from members list
                    const assigneeName = task.assignee ? 
                        (members.find(m => m.id === task.assignee)?.name || task.assignee) : 
                        '-';
                    
                    // Count relationships
                    const relationCount = task.relationships ? task.relationships.length : 0;
                    
                    // Count files
                    const fileCount = task.files ? task.files.length : 0;
                    
                    return `
                    <tr class="task-row" data-task-id="${task.id}" onclick="showTaskDetails('${task.id}')">
                        <td class="task-id">${task.id}</td>
                        <td class="task-title">${task.title}</td>
                        <td><span class="task-status ${task.status ? task.status.toLowerCase() : 'unknown'}">${task.status || 'Unknown'}</span></td>
                        <td>${assigneeName}</td>
                        <td>${task.priority || '-'}</td>
                        <td class="task-relations">${relationCount > 0 ? `<span class="relation-count">${relationCount}</span>` : '-'}</td>
                        <td class="task-files">${fileCount > 0 ? `<span class="file-count">${fileCount}</span>` : '-'}</td>
                    </tr>
                    `;
                }).join('')}
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

// Show matrix instruction message
function showMatrixInstruction() {
    const container = document.getElementById('matrix-container');
    const statsDiv = document.getElementById('matrix-stats');
    
    if (!container) return;
    
    // Hide stats initially
    if (statsDiv) {
        statsDiv.style.display = 'none';
    }
    
    container.innerHTML = `
        <div class="empty-state" style="padding: 60px 20px; text-align: center;">
            <h3 style="color: #666; margin-bottom: 20px;">
                🔍 Configure Filters to Display Traceability Matrix
            </h3>
            <p style="color: #999; font-size: 16px; margin-bottom: 10px;">
                The traceability matrix can be large and may take time to load.
            </p>
            <p style="color: #999; font-size: 16px; margin-bottom: 30px;">
                Please configure your filters above and click <strong>"Apply Filters"</strong> to display the matrix.
            </p>
            <div style="color: #666; font-size: 14px;">
                <p><strong>Available Filters:</strong></p>
                <ul style="list-style: none; padding: 0;">
                    <li>📁 <strong>File Extension</strong> - Filter by file type (.py, .js, etc.)</li>
                    <li>📄 <strong>File Name Contains</strong> - Search for specific file names</li>
                    <li>📋 <strong>Task Name Contains</strong> - Search for specific tasks</li>
                    <li>🔢 <strong>Reference Counts</strong> - Show/hide file reference statistics</li>
                </ul>
            </div>
        </div>
    `;
}

// Load matrix data
async function loadMatrixData(isRefresh = false) {
    try {
        console.log('Loading matrix data. Current project:', currentProject);
        
        // Show loading indicator
        const container = document.getElementById('matrix-container');
        if (container && !isRefresh) {
            container.innerHTML = `
                <div class="loading" style="padding: 60px 20px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 20px;">⏳</div>
                    <h3 style="color: #666;">Loading Traceability Matrix...</h3>
                    <p style="color: #999;">This may take a moment for large datasets.</p>
                </div>
            `;
        }
        
        // Get filter values
        const fileExtension = document.getElementById('matrix-file-extension')?.value || '';
        const fileName = document.getElementById('matrix-file-name')?.value || '';
        const taskName = document.getElementById('matrix-task-name')?.value || '';
        const showRefCounts = document.getElementById('matrix-show-ref-counts')?.checked ?? true;
        
        // Build URL with filters
        let requestUrl = '/api/traceability-matrix/enhanced';
        const params = new URLSearchParams();
        
        if (currentProject) {
            params.append('project_id', currentProject);
        }
        if (fileExtension) {
            params.append('file_extension', fileExtension);
        }
        if (fileName) {
            params.append('file_name_contains', fileName);
        }
        if (taskName) {
            params.append('task_name_contains', taskName);
        }
        params.append('include_reference_counts', showRefCounts);
        
        if (params.toString()) {
            requestUrl += '?' + params.toString();
        }
        
        console.log(`Fetching matrix from: ${requestUrl}`);
        const response = await fetch(requestUrl);
        const matrixData = await response.json();
        console.log('Matrix data:', matrixData);
        
        renderEnhancedMatrix(matrixData);
        
        // Mark that matrix data has been loaded
        matrixDataLoaded = true;
        
        // Setup filter button if not already done
        setupMatrixFilters();
        
    } catch (error) {
        console.error('Error loading matrix data:', error);
        
        // Show error message in container
        const container = document.getElementById('matrix-container');
        if (container) {
            container.innerHTML = `
                <div class="empty-state" style="padding: 40px 20px; text-align: center; color: #e74c3c;">
                    <div style="font-size: 48px; margin-bottom: 20px;">❌</div>
                    <h3>Error Loading Traceability Matrix</h3>
                    <p style="margin-top: 10px;">Failed to load matrix data. Please try again.</p>
                    <p style="font-size: 14px; color: #999; margin-top: 10px;">Error: ${error.message}</p>
                </div>
            `;
        }
        
        // Reset loaded flag on error
        matrixDataLoaded = false;
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

// Render enhanced traceability matrix
function renderEnhancedMatrix(data) {
    const container = document.getElementById('matrix-container');
    if (!container) {
        console.error('Matrix container not found!');
        return;
    }
    
    console.log('Enhanced matrix data:', data);
    console.log('File reference counts:', data.file_reference_counts);
    
    // Store matrix data globally for click handlers
    window.currentMatrixData = data;
    
    // Update statistics
    if (data.summary) {
        document.getElementById('matrix-stats').style.display = 'block';
        document.getElementById('stat-total-tasks').textContent = data.summary.total_tasks;
        document.getElementById('stat-total-files').textContent = data.summary.total_files;
        document.getElementById('stat-total-associations').textContent = data.summary.total_associations;
        document.getElementById('stat-avg-files-per-task').textContent = data.summary.avg_files_per_task;
    }
    
    if (!data || !data.tasks || data.tasks.length === 0 || !data.files || data.files.length === 0) {
        container.innerHTML = '<div class="empty-state">No data matches the current filters.</div>';
        return;
    }
    
    let html = '<div class="matrix-scroll-container"><table class="matrix-table"><thead><tr><th>Task / File</th>';
    
    // Header row with file names and reference counts
    data.files.forEach(file => {
        const fileName = file.split('/').pop();
        const refCount = data.file_reference_counts ? data.file_reference_counts[file] || 0 : 0;
        
        const refCountColor = refCount > 5 ? '#e74c3c' : refCount > 2 ? '#f39c12' : '#27ae60';
        html += `<th title="${file}\n${refCount} reference${refCount !== 1 ? 's' : ''}" style="position: relative;">
            <div style="font-weight: bold;">${fileName}</div>
            <div style="font-size: 12px; color: ${refCountColor}; font-weight: bold; 
                        background: ${refCountColor}20; 
                        padding: 2px 6px; 
                        border-radius: 12px; 
                        display: inline-block;
                        margin-top: 4px;">
                ${refCount}
            </div>
        </th>`;
    });
    
    html += '</tr></thead><tbody>';
    
    // Task rows
    data.tasks.forEach((task, taskIndex) => {
        const statusClass = task.status ? `status-${task.status.toLowerCase()}` : '';
        html += `<tr>
            <th onclick="showTaskDetails('${task.id}')" class="clickable-task ${statusClass}" title="Click to view task details">
                ${task.title}
                <span style="font-size: 11px; color: #666; display: block;">
                    ${task.status} | ${task.assignee || 'Unassigned'}
                </span>
            </th>`;
        
        // For each file, show relationship
        data.matrix[taskIndex].forEach((hasRelation, fileIndex) => {
            if (hasRelation) {
                const file = data.files[fileIndex];
                const fileName = file.split('/').pop();
                html += `<td class="matrix-cell has-relation clickable-relation" 
                    onclick="showFileTaskRelation(${taskIndex}, ${fileIndex})" 
                    title="Task: ${task.title}\nFile: ${fileName}\n\nClick to see all tasks referencing this file">●</td>`;
            } else {
                html += `<td class="matrix-cell"></td>`;
            }
        });
        
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    // Add most referenced files if available
    if (data.summary && data.summary.most_referenced_files && data.summary.most_referenced_files.length > 0) {
        html += '<div style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px;">';
        html += '<h4 style="margin-top: 0;">Most Referenced Files</h4>';
        html += '<ol style="margin: 0; padding-left: 20px;">';
        
        data.summary.most_referenced_files.forEach(([file, count]) => {
            const fileName = file.split('/').pop();
            html += `<li>${fileName} - ${count} references</li>`;
        });
        
        html += '</ol></div>';
    }
    
    container.innerHTML = html;
}

// Setup matrix filters
function setupMatrixFilters() {
    try {
        const applyButton = document.getElementById('apply-matrix-filters');
        if (applyButton && !applyButton.hasListener) {
            applyButton.hasListener = true;
            applyButton.addEventListener('click', () => {
                loadMatrixData();
            });
        }
        
        // Load file extensions dynamically
        loadFileExtensions();
        
        // Add Enter key support for text inputs
        const textInputs = document.querySelectorAll('#matrix-file-name, #matrix-task-name');
        if (textInputs) {
            textInputs.forEach(input => {
                if (input) {
                    input.addEventListener('keypress', (e) => {
                        if (e.key === 'Enter') {
                            loadMatrixData();
                        }
                    });
                }
            });
        }
    } catch (error) {
        console.error('Error in setupMatrixFilters:', error);
    }
}

// Load available file extensions
async function loadFileExtensions() {
    if (!currentProject) return;
    
    try {
        const response = await fetch(`/api/traceability-matrix/file-extensions?project_id=${currentProject}`);
        const extensions = await response.json();
        
        const select = document.getElementById('matrix-file-extension');
        if (select && extensions.length > 0) {
            // Keep the "All" option
            const currentValue = select.value;
            select.innerHTML = '<option value="">All</option>';
            
            // Add dynamic extensions
            extensions.forEach(ext => {
                const option = document.createElement('option');
                option.value = ext;
                option.textContent = ext;
                select.appendChild(option);
            });
            
            // Restore previous selection if still valid
            if (currentValue && extensions.includes(currentValue)) {
                select.value = currentValue;
            }
        }
    } catch (error) {
        console.error('Error loading file extensions:', error);
    }
}

// Show member details
async function showMemberDetails(memberId) {
    const member = members.find(m => m.id === memberId);
    if (!member) {
        console.error(`Member not found: ${memberId}`);
        return;
    }
    
    const modal = document.getElementById('member-modal');
    const content = document.getElementById('member-details');
    
    content.innerHTML = `
        <h2>${member.name}</h2>
        <div class="member-photo large clickable-photo" onclick="event.stopPropagation(); openPhotoUpload('${member.id}')" title="Click to change photo">
            ${member.avatar_url || member.profile_image_path 
                ? `<img src="${member.avatar_url || member.profile_image_path}" alt="${member.name}">` 
                : member.name.charAt(0)
            }
            <div class="photo-overlay">
                <span>📷 Change Photo</span>
            </div>
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
                        <li class="task-detail-item">
                            <span class="task-status ${task.status.toLowerCase()}">${task.status}</span>
                            <button class="task-btn ${task.status.toLowerCase()}" onclick="event.stopPropagation(); showTaskDetails('${task.id}')">${task.id}</button>
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
async function showTaskDetails(taskId) {
    try {
        console.log(`Opening task details for: ${taskId}`);
        
        let task = tasks.find(t => t.id === taskId);
        if (!task) {
            // Try to fetch task details from API
            try {
                console.log(`Task not in cache, fetching from API: ${taskId}`);
                const response = await fetch(`/api/tasks/${taskId}`);
                if (response.ok) {
                    task = await response.json();
                    console.log(`Fetched task from API:`, task);
                    // Add to tasks array for future reference
                    tasks.push(task);
                } else {
                    console.error(`Task not found: ${taskId}, Status: ${response.status}`);
                    alert(`Task ${taskId} not found`);
                    return;
                }
            } catch (error) {
                console.error(`Error fetching task ${taskId}:`, error);
                alert(`Error loading task details: ${error.message}`);
                return;
            }
        }
        
        const modal = document.getElementById('task-modal');
        const content = document.getElementById('task-details');
        
        if (!modal || !content) {
            console.error('Task modal elements not found in DOM');
            return;
        }
        
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
                    <option value="" ${!task.assignee || task.assignee === null ? 'selected' : ''}>Unassigned</option>
                    ${memberOptions}
                </select>
            </p>
            <p><strong>Priority:</strong> ${task.priority || 'Not set'}</p>
            <p><strong>Description:</strong> ${task.description || 'No description'}</p>
        </div>
        
        <div class="detail-section">
            <h3>Task Relationships</h3>
            ${(() => {
                console.log('Rendering relationships for task:', task.id);
                console.log('Relationships data:', task.relationships);
                
                if (task.relationships && Array.isArray(task.relationships) && task.relationships.length > 0) {
                    return `<div class="relationships-container">
                        ${renderTaskRelationships(task.relationships, task.id)}
                      </div>`;
                } else {
                    return '<p>No task relationships</p>';
                }
            })()}
        </div>
        
        <div class="detail-section">
            <h3>Related Files</h3>
            ${(() => {
                console.log('Rendering files for task:', task.id);
                console.log('Files data:', task.files);
                
                if (task.files && Array.isArray(task.files) && task.files.length > 0) {
                    return `<ul class="file-list">
                        ${task.files.map(f => `<li>
                            <span class="file-path" data-file-path="${f.file_path}" style="cursor: pointer; color: #007bff; text-decoration: underline;">
                                ${f.file_path}
                            </span>
                            ${f.description ? ` - ${f.description}` : ''}
                        </li>`).join('')}
                      </ul>`;
                } else {
                    return '<p>No files associated</p>';
                }
            })()}
        </div>
    `;
    
        modal.style.display = 'block';
        
        // Make file links clickable
        setTimeout(() => {
            makeFileLinksClickable(content);
        }, 100);
        
    } catch (error) {
        console.error('Error in showTaskDetails:', error);
        alert(`Error displaying task details: ${error.message}`);
    }
}

// Render task relationships with clickable links
function renderTaskRelationships(relationships, currentTaskId) {
    console.log('renderTaskRelationships called with:', relationships, 'for task:', currentTaskId);
    
    if (!relationships || !Array.isArray(relationships) || relationships.length === 0) {
        return '<p>No relationships found</p>';
    }
    
    const parentRelations = relationships.filter(r => r.child_id === currentTaskId);
    const childRelations = relationships.filter(r => r.parent_id === currentTaskId);
    
    console.log('Parent relations:', parentRelations);
    console.log('Child relations:', childRelations);
    
    let html = '';
    
    // Parent tasks (tasks this task depends on)
    if (parentRelations.length > 0) {
        html += '<div class="relationship-group">';
        html += '<h4>⬆️ Parent Tasks</h4>';
        html += '<ul class="relationship-list">';
        parentRelations.forEach(rel => {
            const relatedTask = tasks.find(t => t.id === rel.parent_id);
            const taskTitle = relatedTask ? relatedTask.title : 'Unknown Task';
            const relationshipIcon = getRelationshipIcon(rel.relationship_type, 'parent');
            html += `<li class="relationship-item">
                ${relationshipIcon}
                <span class="relationship-type">${rel.relationship_type}</span>
                <a href="#" class="task-link" onclick="event.preventDefault(); showTaskDetails('${rel.parent_id}')">${rel.parent_id}</a>
                <span class="task-title-small">${taskTitle}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }
    
    // Child tasks (tasks that depend on this task)
    if (childRelations.length > 0) {
        html += '<div class="relationship-group">';
        html += '<h4>⬇️ Child Tasks</h4>';
        html += '<ul class="relationship-list">';
        childRelations.forEach(rel => {
            const relatedTask = tasks.find(t => t.id === rel.child_id);
            const taskTitle = relatedTask ? relatedTask.title : 'Unknown Task';
            const relationshipIcon = getRelationshipIcon(rel.relationship_type, 'child');
            html += `<li class="relationship-item">
                ${relationshipIcon}
                <span class="relationship-type">${rel.relationship_type}</span>
                <a href="#" class="task-link" onclick="event.preventDefault(); showTaskDetails('${rel.child_id}')">${rel.child_id}</a>
                <span class="task-title-small">${taskTitle}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }
    
    return html || '<p>No relationships found</p>';
}

// Get icon for relationship type
function getRelationshipIcon(relationshipType, direction) {
    const icons = {
        'parent-child': direction === 'parent' ? '📋' : '📝',
        'blocks': direction === 'parent' ? '🚫' : '⏸️',
        'depends-on': direction === 'parent' ? '🔗' : '🔄',
        'related': '🔗'
    };
    return icons[relationshipType] || '📎';
}

// Setup task view switcher
function setupTaskViewSwitcher() {
    const taskModeButtons = document.querySelectorAll('.task-mode-btn');
    
    taskModeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const mode = button.dataset.mode;
            
            // Update button states
            taskModeButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Hide all task containers
            document.getElementById('tasks-list').style.display = 'none';
            document.getElementById('tasks-hierarchy').style.display = 'none';
            document.getElementById('tasks-kanban').style.display = 'none';
            
            // Show selected container
            if (mode === 'list') {
                document.getElementById('tasks-list').style.display = 'block';
                loadTasksData(); // Reload list view
            } else if (mode === 'hierarchy') {
                document.getElementById('tasks-hierarchy').style.display = 'block';
                loadTaskHierarchy(); // Load hierarchy view
            } else if (mode === 'kanban') {
                document.getElementById('tasks-kanban').style.display = 'block';
                loadTaskKanban(); // Load kanban view
            }
        });
    });
}

// Load task hierarchy view
async function loadTaskHierarchy() {
    console.log('Loading task hierarchy...');
    
    if (!currentProject) {
        console.warn('No current project selected');
        return;
    }
    
    try {
        const response = await fetch(`/api/tasks?project_id=${currentProject}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const allTasks = await response.json();
        tasks = allTasks; // Update global tasks
        
        const hierarchyContainer = document.getElementById('tasks-hierarchy');
        
        // Build hierarchy tree
        const rootTasks = findRootTasks(allTasks);
        const hierarchyHTML = buildTaskTree(rootTasks, allTasks);
        
        hierarchyContainer.innerHTML = `
            <div class="hierarchy-header">
                <h3>🌳 Task Hierarchy</h3>
                <p>Click on task IDs to view details. Parent-child relationships are shown as indented trees.</p>
            </div>
            <div class="hierarchy-tree">
                ${hierarchyHTML}
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading task hierarchy:', error);
        document.getElementById('tasks-hierarchy').innerHTML = 
            '<div class="error">Failed to load task hierarchy</div>';
    }
}

// Find root tasks (tasks with no parents)
function findRootTasks(allTasks) {
    const childTaskIds = new Set();
    
    // Collect all child task IDs
    allTasks.forEach(task => {
        if (task.relationships) {
            task.relationships.forEach(rel => {
                if (rel.relationship_type === 'parent-child' && rel.parent_id !== task.id) {
                    childTaskIds.add(task.id);
                }
                if (rel.relationship_type === 'parent-child' && rel.child_id !== task.id) {
                    childTaskIds.add(rel.child_id);
                }
            });
        }
    });
    
    // Root tasks are those not in the child set
    return allTasks.filter(task => !childTaskIds.has(task.id));
}

// Build task tree HTML
function buildTaskTree(rootTasks, allTasks, level = 0) {
    let html = '';
    
    rootTasks.forEach(task => {
        const indent = '　'.repeat(level); // Japanese space for better indentation
        const children = findChildTasks(task.id, allTasks);
        const hasChildren = children.length > 0;
        
        html += `
            <div class="tree-node" style="margin-left: ${level * 20}px;">
                <div class="tree-item ${hasChildren ? 'has-children' : ''}">
                    ${hasChildren ? '📁' : '📄'}
                    <span class="task-id-link" onclick="showTaskDetails('${task.id}')">${task.id}</span>
                    <span class="task-title">${task.title}</span>
                    <span class="task-status task-status-${task.status.toLowerCase()}">${task.status}</span>
                    <span class="task-assignee">${task.assignee || 'Unassigned'}</span>
                </div>
                ${hasChildren ? buildTaskTree(children, allTasks, level + 1) : ''}
            </div>
        `;
    });
    
    return html;
}

// Find child tasks for a given parent
function findChildTasks(parentId, allTasks) {
    const childIds = [];
    
    // Find children in the parent's relationships
    const parentTask = allTasks.find(t => t.id === parentId);
    if (parentTask && parentTask.relationships) {
        parentTask.relationships.forEach(rel => {
            if (rel.relationship_type === 'parent-child' && rel.parent_id === parentId) {
                childIds.push(rel.child_id);
            }
        });
    }
    
    return allTasks.filter(task => childIds.includes(task.id));
}

// Load kanban view
async function loadTaskKanban() {
    console.log('Loading task kanban...');
    
    // Make sure we have tasks loaded
    if (!tasks || tasks.length === 0) {
        await loadTasksData();
    }
    
    // Group tasks by status
    const tasksByStatus = {
        'TODO': [],
        'READY': [],
        'DOING': [],
        'TESTING': [],
        'DONE': []
    };
    
    // Organize tasks into columns
    tasks.forEach(task => {
        const status = task.status || 'TODO';
        if (tasksByStatus[status]) {
            tasksByStatus[status].push(task);
        } else {
            // Handle custom statuses
            tasksByStatus['TODO'].push(task);
        }
    });
    
    // Build kanban HTML
    let kanbanHTML = `
        <div class="kanban-header">
            <h3>🗃️ Kanban Board</h3>
            <p>Drag and drop tasks to change their status</p>
        </div>
        <div class="kanban-board">
    `;
    
    // Create columns for each status
    Object.entries(tasksByStatus).forEach(([status, statusTasks]) => {
        const columnClass = `kanban-column status-${status.toLowerCase()}`;
        const taskCount = statusTasks.length;
        
        kanbanHTML += `
            <div class="${columnClass}" data-status="${status}">
                <div class="kanban-column-header">
                    <h4>${status}</h4>
                    <span class="task-count">${taskCount}</span>
                </div>
                <div class="kanban-tasks" ondrop="handleTaskDrop(event, '${status}')" ondragover="allowDrop(event)" ondragleave="handleDragLeave(event)">
        `;
        
        // Add tasks to column
        statusTasks.forEach(task => {
            const assigneeName = task.assignee ? 
                (members.find(m => m.id === task.assignee)?.name || task.assignee) : 
                'Unassigned';
            
            kanbanHTML += `
                <div class="kanban-task" draggable="true" ondragstart="handleDragStart(event, '${task.id}')" ondragend="handleDragEnd(event)" onclick="showTaskDetails('${task.id}')" data-task-id="${task.id}">
                    <div class="kanban-task-header">
                        <span class="kanban-task-id">${task.id}</span>
                        <span class="kanban-task-priority priority-${task.priority || 3}">P${task.priority || 3}</span>
                    </div>
                    <div class="kanban-task-title">${task.title}</div>
                    <div class="kanban-task-footer">
                        <span class="kanban-task-assignee">${assigneeName}</span>
                    </div>
                </div>
            `;
        });
        
        kanbanHTML += `
                </div>
            </div>
        `;
    });
    
    kanbanHTML += '</div>';
    
    // Add CSS for kanban if not already present
    if (!document.getElementById('kanban-styles')) {
        const style = document.createElement('style');
        style.id = 'kanban-styles';
        style.textContent = `
            .kanban-board {
                display: flex;
                gap: 20px;
                padding: 20px;
                overflow-x: auto;
                min-height: 600px;
                background: #f5f5f5;
            }
            
            .kanban-column {
                flex: 1;
                min-width: 300px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                flex-direction: column;
            }
            
            .kanban-column-header {
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px 8px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid #e0e0e0;
            }
            
            .kanban-column-header h4 {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
            }
            
            .kanban-column-header .task-count {
                background: #e0e0e0;
                color: #666;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 14px;
            }
            
            .kanban-tasks {
                flex: 1;
                padding: 10px;
                overflow-y: auto;
                min-height: 400px;
            }
            
            .kanban-task {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 10px;
                cursor: move;
                transition: all 0.2s;
            }
            
            .kanban-task:hover {
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transform: translateY(-2px);
            }
            
            .kanban-task.dragging {
                opacity: 0.5;
            }
            
            .kanban-task-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
            }
            
            .kanban-task-id {
                font-size: 12px;
                color: #666;
                font-weight: 600;
            }
            
            .kanban-task-priority {
                font-size: 11px;
                padding: 2px 6px;
                border-radius: 4px;
                background: #f0f0f0;
                color: #666;
            }
            
            .kanban-task-priority.priority-1 { background: #fee; color: #f44; }
            .kanban-task-priority.priority-2 { background: #fef; color: #f4f; }
            .kanban-task-priority.priority-3 { background: #ffe; color: #880; }
            .kanban-task-priority.priority-4 { background: #efe; color: #080; }
            .kanban-task-priority.priority-5 { background: #eef; color: #008; }
            
            .kanban-task-title {
                font-size: 14px;
                margin-bottom: 8px;
                line-height: 1.4;
            }
            
            .kanban-task-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .kanban-task-assignee {
                font-size: 12px;
                color: #666;
                background: #f0f0f0;
                padding: 2px 8px;
                border-radius: 4px;
            }
            
            .kanban-column.drag-over {
                background-color: #f0f8ff;
                border: 2px dashed #007bff;
            }
            
            /* Status-specific column styling */
            .kanban-column.status-todo .kanban-column-header { background: #f8f9fa; }
            .kanban-column.status-ready .kanban-column-header { background: #fff3cd; }
            .kanban-column.status-doing .kanban-column-header { background: #d1ecf1; }
            .kanban-column.status-testing .kanban-column-header { background: #d4edda; }
            .kanban-column.status-done .kanban-column-header { background: #d6d8d9; }
        `;
        document.head.appendChild(style);
    }
    
    document.getElementById('tasks-kanban').innerHTML = kanbanHTML;
}

// Drag and drop handlers for Kanban
let draggedTaskId = null;

function handleDragStart(event, taskId) {
    draggedTaskId = taskId;
    event.target.classList.add('dragging');
    event.dataTransfer.effectAllowed = 'move';
}

function handleDragEnd(event) {
    event.target.classList.remove('dragging');
    // Remove all drag-over classes
    document.querySelectorAll('.kanban-column').forEach(col => {
        col.classList.remove('drag-over');
    });
}

function allowDrop(event) {
    event.preventDefault();
    event.currentTarget.parentElement.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.currentTarget.parentElement.classList.remove('drag-over');
}

function handleTaskDrop(event, newStatus) {
    event.preventDefault();
    event.currentTarget.parentElement.classList.remove('drag-over');
    
    if (draggedTaskId) {
        updateTaskStatus(draggedTaskId, newStatus);
        
        // Update local task status immediately for responsive UI
        const task = tasks.find(t => t.id === draggedTaskId);
        if (task) {
            task.status = newStatus;
        }
        
        // Reload kanban to reflect changes
        setTimeout(() => loadTaskKanban(), 100);
    }
    
    draggedTaskId = null;
}

// Make drag/drop functions global
window.handleDragStart = handleDragStart;
window.handleDragEnd = handleDragEnd;
window.allowDrop = allowDrop;
window.handleDragLeave = handleDragLeave;
window.handleTaskDrop = handleTaskDrop;

// Photo upload functionality
function openPhotoUpload(memberId) {
    console.log('Opening photo upload for member:', memberId);
    currentMemberId = memberId;
    
    const cropModal = document.getElementById('crop-modal');
    cropModal.innerHTML = `
        <div class="crop-modal-content">
            <div class="crop-modal-header">
                <h3>📷 Change Member Photo</h3>
                <button class="close-crop" onclick="closePhotoUpload()">&times;</button>
            </div>
            <div class="crop-modal-body">
                <div class="upload-section">
                    <label for="photo-input" class="upload-label">
                        📁 Choose Photo
                        <input type="file" id="photo-input" accept="image/*" onchange="handlePhotoSelect(event)" style="display: none;">
                    </label>
                    <p class="upload-hint">Select a JPG, PNG, or GIF image</p>
                </div>
                <div id="crop-section" style="display: none;">
                    <div id="crop-container">
                        <img id="crop-image" style="max-width: 100%; max-height: 400px;">
                    </div>
                    <div class="crop-controls">
                        <button class="btn-primary" onclick="cropAndSave()">✂️ Crop & Save</button>
                        <button class="btn-secondary" onclick="cancelCrop()">❌ Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    cropModal.style.display = 'block';
}

function closePhotoUpload() {
    const cropModal = document.getElementById('crop-modal');
    cropModal.style.display = 'none';
    
    // Clean up cropper if it exists
    if (currentCropper) {
        currentCropper.destroy();
        currentCropper = null;
    }
    
    currentMemberId = null;
}

function handlePhotoSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please select a valid image file');
        return;
    }
    
    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
        alert('File size must be less than 5MB');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const cropImage = document.getElementById('crop-image');
        cropImage.src = e.target.result;
        
        // Show crop section
        document.getElementById('crop-section').style.display = 'block';
        
        // Initialize cropper with Cropper.js
        if (currentCropper) {
            currentCropper.destroy();
        }
        
        // Wait for image to load then initialize cropper
        cropImage.onload = function() {
            if (typeof Cropper !== 'undefined') {
                currentCropper = new Cropper(cropImage, {
                    aspectRatio: 1, // Square crop
                    viewMode: 1,
                    dragMode: 'move',
                    cropBoxResizable: true,
                    cropBoxMovable: true,
                    toggleDragModeOnDblclick: false,
                    modal: true,
                    background: true,
                    responsive: true,
                    restore: false,
                    guides: true,
                    center: true,
                    highlight: true,
                    movable: true,
                    rotatable: true,
                    scalable: true,
                    zoomable: true,
                    zoomOnTouch: true,
                    zoomOnWheel: true,
                    wheelZoomRatio: 0.1,
                    minCropBoxWidth: 50,
                    minCropBoxHeight: 50,
                    ready: function() {
                        console.log('Cropper ready for:', file.name);
                    }
                });
            } else {
                console.warn('Cropper.js not available, using simple crop');
            }
        };
    };
    
    reader.readAsDataURL(file);
}

function cancelCrop() {
    document.getElementById('crop-section').style.display = 'none';
    document.getElementById('photo-input').value = '';
    
    if (currentCropper) {
        currentCropper.destroy();
        currentCropper = null;
    }
}

async function cropAndSave() {
    if (!currentMemberId) {
        alert('No member selected');
        return;
    }
    
    let canvas;
    
    // Use Cropper.js if available and initialized
    if (currentCropper && typeof Cropper !== 'undefined') {
        console.log('Using Cropper.js for cropping');
        canvas = currentCropper.getCroppedCanvas({
            width: 200,
            height: 200,
            imageSmoothingEnabled: true,
            imageSmoothingQuality: 'high'
        });
    } else {
        // Fallback to simple cropping
        console.log('Using fallback cropping method');
        const cropImage = document.getElementById('crop-image');
        canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Simple cropping to square format
        const size = Math.min(cropImage.naturalWidth, cropImage.naturalHeight);
        canvas.width = 200;
        canvas.height = 200;
        
        // Draw cropped image
        ctx.drawImage(
            cropImage,
            (cropImage.naturalWidth - size) / 2,
            (cropImage.naturalHeight - size) / 2,
            size,
            size,
            0,
            0,
            200,
            200
        );
    }
    
    // Convert to blob and upload
    canvas.toBlob(async (blob) => {
        if (!blob) {
            alert('Failed to process image');
            return;
        }
        
        try {
            // Show loading state
            const cropBtn = document.querySelector('.btn-primary');
            const originalText = cropBtn.textContent;
            cropBtn.textContent = '⏳ Uploading...';
            cropBtn.disabled = true;
            
            await uploadMemberPhoto(currentMemberId, blob);
            
        } catch (error) {
            console.error('Error uploading photo:', error);
            alert('Failed to upload photo: ' + error.message);
            
            // Restore button state
            const cropBtn = document.querySelector('.btn-primary');
            cropBtn.textContent = '✂️ Crop & Save';
            cropBtn.disabled = false;
        }
    }, 'image/jpeg', 0.9);
}

async function uploadMemberPhoto(memberId, photoBlob) {
    const formData = new FormData();
    formData.append('file', photoBlob, 'profile.jpg');
    
    try {
        const response = await fetch(`/api/members/${memberId}/upload-photo`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }
        
        const result = await response.json();
        console.log('Photo uploaded successfully:', result);
        
        // Close modal
        closePhotoUpload();
        
        // Refresh member data
        await loadTeamData();
        
        // Show success message
        showUpdateIndicator('📷 Photo updated successfully!');
        
        // Refresh the current member modal if it's open
        if (document.getElementById('member-modal').style.display === 'block') {
            showMemberDetails(currentMemberId);
        }
        
    } catch (error) {
        console.error('Error uploading photo:', error);
        throw error;
    }
}

// Make functions globally available
window.openPhotoUpload = openPhotoUpload;
window.closePhotoUpload = closePhotoUpload;
window.handlePhotoSelect = handlePhotoSelect;
window.cancelCrop = cancelCrop;
window.cropAndSave = cropAndSave;

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
    
    // Handle empty assignee (Unassigned) - send empty string for better compatibility
    let assigneeValue;
    if (newAssignee === "" || newAssignee === null || newAssignee === undefined) {
        // Send empty string for unassigned
        assigneeValue = "";
        console.log(`Sending assignee value: "" (empty string for unassigned)`);
    } else {
        assigneeValue = newAssignee;
        console.log(`Sending assignee value: ${assigneeValue}`);
    }
    
    try {
        console.log('Updating task assignee via PUT /api/tasks/{id}/assignee');
        const response = await fetch(`/api/tasks/${taskId}/assignee`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ assignee: assigneeValue })
        });
        
        if (!response.ok) {
            // Handle error response
            console.error('Response status:', response.status);
            console.error('Response statusText:', response.statusText);
            
            let errorMessage = 'Unknown error';
            try {
                const errorData = await response.json();
                console.error('Error response data:', errorData);
                errorMessage = errorData.detail || errorData.message || JSON.stringify(errorData);
            } catch (e) {
                console.error('Failed to parse error response as JSON');
                const errorText = await response.text();
                console.error('Error response text:', errorText);
                errorMessage = errorText || `HTTP ${response.status} ${response.statusText}`;
            }
            
            alert(`Failed to update assignee: ${errorMessage}`);
            return;
        }
        
        // Parse response
        const data = await response.json();
        console.log('Task assignee updated:', data);
        
        // Update local task
        const task = tasks.find(t => t.id === taskId);
        if (task) {
            // Store the assignee value (could be null for unassigned)
            task.assignee = assigneeValue;
            
            // Refresh task list
            renderTasks(tasks);
            
            // Get assignee name for display
            const assigneeName = assigneeValue ? 
                (members.find(m => m.id === assigneeValue)?.name || assigneeValue) : 
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
    // Setup auto-refresh checkbox
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.addEventListener('change', (e) => {
            isAutoRefreshEnabled = e.target.checked;
            console.log('Auto-refresh', isAutoRefreshEnabled ? 'enabled' : 'disabled');
        });
    }
    
    // Clear any existing interval first
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(() => {
        if (isAutoRefreshEnabled && currentProject) {
            const timestamp = new Date().toLocaleTimeString();
            console.log(`[${timestamp}] Auto-refreshing data for project: ${currentProject}`);
            showUpdateIndicator('Auto-refreshing...');
            loadCurrentTabData();
        } else {
            console.log(`Auto-refresh skipped: enabled=${isAutoRefreshEnabled}, project=${currentProject}`);
        }
    }, REFRESH_INTERVAL);
    
    console.log(`Auto-refresh interval started (${REFRESH_INTERVAL/1000} seconds)`);
}

// Make key functions available globally at the end of the file
// This must be at the end after all functions are defined
window.loadTeamData = loadTeamData;
window.changeViewMode = function(mode) {
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
};
// Load database configuration info for settings tab
async function loadDatabaseInfo() {
    const container = document.getElementById('database-info');
    if (!container) return;
    
    try {
        console.log('Loading database configuration info...');
        console.log('Current URL:', window.location.href);
        console.log('Fetching:', '/api/database-info');
        const response = await fetch('/api/database-info');
        
        console.log('Response status:', response.status);
        console.log('Response URL:', response.url);
        
        if (!response.ok) {
            console.error('Failed response:', response);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Database info received:', data);
        
        // Build the info display
        let html = '<div class="database-config">';
        
        // Database type
        html += `
            <div class="info-row">
                <div class="info-label">Database Type:</div>
                <div class="info-value">${(data.type || 'unknown').toUpperCase()}</div>
            </div>
        `;
        
        // Database status
        html += `
            <div class="info-row">
                <div class="info-label">Status:</div>
                <div class="info-value">${data.status || 'unknown'}</div>
            </div>
        `;
        
        // Connection details
        if (data.details) {
            html += '<div class="info-row"><div class="info-label">Connection Details:</div><div class="info-value"></div></div>';
            
            Object.entries(data.details).forEach(([key, value]) => {
                if (key !== 'password') { // Don't show password
                    html += `
                        <div class="info-row" style="margin-left: 20px;">
                            <div class="info-label">${key}:</div>
                            <div class="info-value">${value}</div>
                        </div>
                    `;
                }
            });
        }
        
        // Timestamp (if available)
        if (data.timestamp) {
            const timestamp = new Date(data.timestamp).toLocaleString();
            html += `
                <div class="info-row">
                    <div class="info-label">Last Updated:</div>
                    <div class="info-value">${timestamp}</div>
                </div>
            `;
        }
        
        html += '</div>';
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading database info:', error);
        container.innerHTML = '<p class="error">Failed to load database information: ' + error.message + '</p>';
    }
}

// Load project settings
async function loadProjectSettings() {
    if (!currentProject) {
        document.getElementById('project-settings-content').innerHTML = 
            '<p class="warning">Please select a project to view its settings.</p>';
        document.getElementById('strict-mode-settings').style.display = 'none';
        return;
    }
    
    try {
        console.log('Loading project settings for:', currentProject);
        const url = `/api/projects/${currentProject}/settings`;
        console.log('Fetching from URL:', url);
        
        const response = await fetch(url);
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        const settings = await response.json();
        console.log('Project settings:', settings);
        
        // Update UI
        document.getElementById('project-settings-content').innerHTML = 
            `<p>Viewing settings for project: <strong>${currentProject}</strong></p>`;
        
        // Show project root setting
        document.getElementById('project-root-setting').style.display = 'block';
        
        // Show strict mode settings
        document.getElementById('strict-mode-settings').style.display = 'block';
        
        // Set project root value
        const projectRoot = document.getElementById('project-root');
        if (projectRoot) {
            projectRoot.value = settings.project_root || '';
        }
        
        // Set checkbox states
        document.getElementById('strict-doc-read').checked = settings.strict_doc_read || false;
        document.getElementById('strict-file-ref').checked = settings.strict_file_ref || false;
        document.getElementById('strict-log-entry').checked = settings.strict_log_entry || false;
        
        // Store settings globally
        window.projectSettings = settings;
        
        // Setup save button
        setupProjectSettingsSave();
        
    } catch (error) {
        console.error('Error loading project settings:', error);
        document.getElementById('project-settings-content').innerHTML = 
            '<p class="error">Failed to load project settings: ' + error.message + '</p>';
    }
}

// Setup project settings save
function setupProjectSettingsSave() {
    const saveButton = document.getElementById('save-project-settings');
    const statusDiv = document.getElementById('settings-save-status');
    
    saveButton.onclick = async () => {
        try {
            const settings = {
                strict_doc_read: document.getElementById('strict-doc-read').checked,
                strict_file_ref: document.getElementById('strict-file-ref').checked,
                strict_log_entry: document.getElementById('strict-log-entry').checked,
                project_root: document.getElementById('project-root').value.trim()
            };
            
            console.log('Saving project settings:', settings);
            
            const response = await fetch(`/api/projects/${currentProject}/settings`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            
            if (response.ok) {
                statusDiv.style.display = 'block';
                statusDiv.style.color = 'green';
                statusDiv.textContent = 'Settings saved successfully!';
                
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 3000);
            } else {
                throw new Error('Failed to save settings');
            }
            
        } catch (error) {
            console.error('Error saving project settings:', error);
            statusDiv.style.display = 'block';
            statusDiv.style.color = 'red';
            statusDiv.textContent = 'Failed to save settings: ' + error.message;
        }
    };
}

// Load settings data when settings tab is opened
function loadSettings() {
    console.log('Loading settings...');
    loadDatabaseInfo();
    loadProjectSettings();
    loadProjectStatistics();
}

// Show file-task relation details
async function showFileTaskRelation(taskIndex, fileIndex) {
    const data = window.currentMatrixData;
    if (!data) {
        console.error('No matrix data available');
        return;
    }
    
    const task = data.tasks[taskIndex];
    const file = data.files[fileIndex];
    const fileName = file.split('/').pop();
    
    console.log(`Showing relation: Task "${task.title}" <-> File "${fileName}"`);
    
    // Create a modal for showing relation details
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.style.zIndex = '9999';
    
    // Get all tasks that reference this file
    const relatedTasks = [];
    data.tasks.forEach((t, idx) => {
        if (data.matrix[idx][fileIndex]) {
            relatedTasks.push({
                ...t,
                isCurrentTask: idx === taskIndex
            });
        }
    });
    
    let modalContent = `
        <div class="modal-content" style="max-width: 800px;">
            <span class="close" onclick="this.closest('.modal').remove()">&times;</span>
            <h2>File-Task Relationship</h2>
            
            <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #2c3e50;">File Information</h3>
                <p><strong>File:</strong> ${fileName}</p>
                <p><strong>Full Path:</strong> <code class="file-path" data-file-path="${file}" style="background: #e9ecef; padding: 2px 5px; border-radius: 3px; cursor: pointer; color: #007bff; text-decoration: underline;">${file}</code></p>
                <p><strong>Total References:</strong> ${relatedTasks.length}</p>
            </div>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #1976d2;">Current Task</h3>
                <div onclick="showTaskDetails('${task.id}')" style="cursor: pointer; padding: 10px; background: white; border-radius: 4px;">
                    <strong>${task.title}</strong>
                    <div style="font-size: 14px; color: #666; margin-top: 5px;">
                        Status: <span class="task-status ${task.status}">${task.status}</span> | 
                        Assignee: ${task.assignee || 'Unassigned'} |
                        Priority: ${task.priority || 'N/A'}
                    </div>
                </div>
            </div>
            
            <div>
                <h3 style="color: #2c3e50;">All Tasks Referencing This File (${relatedTasks.length})</h3>
                <div style="max-height: 400px; overflow-y: auto;">
    `;
    
    relatedTasks.forEach(relatedTask => {
        const highlight = relatedTask.isCurrentTask ? 'background: #fffde7; border: 2px solid #fbc02d;' : 'background: white;';
        modalContent += `
            <div onclick="showTaskDetails('${relatedTask.id}')" 
                 style="cursor: pointer; padding: 10px; margin-bottom: 10px; border-radius: 4px; ${highlight} border: 1px solid #ddd;">
                <strong>${relatedTask.title}</strong>
                ${relatedTask.isCurrentTask ? '<span style="color: #f57c00; margin-left: 10px;">(Current)</span>' : ''}
                <div style="font-size: 14px; color: #666; margin-top: 5px;">
                    Status: <span class="task-status ${relatedTask.status}">${relatedTask.status}</span> | 
                    Assignee: ${relatedTask.assignee || 'Unassigned'} |
                    Priority: ${relatedTask.priority || 'N/A'}
                </div>
            </div>
        `;
    });
    
    modalContent += `
                </div>
            </div>
            
            <div style="margin-top: 20px; text-align: right;">
                <button onclick="this.closest('.modal').remove()" 
                        style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    Close
                </button>
            </div>
        </div>
    `;
    
    modal.innerHTML = modalContent;
    document.body.appendChild(modal);
    
    // Make file path clickable
    setTimeout(() => {
        makeFileLinksClickable(modal);
    }, 100);
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// File Viewer Functions
let currentFileViewer = null;

// View file in modal
async function viewFile(filePath, taskId = null) {
    console.log(`Opening file viewer for: ${filePath}`);
    
    const modal = document.getElementById('file-viewer-modal');
    const loadingDiv = document.getElementById('file-viewer-loading');
    const contentDiv = document.getElementById('file-content-display');
    const errorDiv = document.getElementById('file-viewer-error');
    const infoDiv = document.getElementById('file-viewer-info');
    
    // Show modal and loading state
    modal.style.display = 'block';
    loadingDiv.style.display = 'block';
    contentDiv.style.display = 'none';
    errorDiv.style.display = 'none';
    
    // Enable copy buttons initially
    const pathBtn = document.getElementById('copy-file-path-btn');
    const contentBtn = document.getElementById('copy-file-content-btn');
    if (pathBtn) {
        pathBtn.disabled = false;
        pathBtn.style.opacity = '1';
        pathBtn.style.cursor = 'pointer';
    }
    if (contentBtn) {
        contentBtn.disabled = false;
        contentBtn.style.opacity = '1';
        contentBtn.style.cursor = 'pointer';
    }
    
    try {
        // Build API URL with current project
        let apiUrl = `/api/files/view?file_path=${encodeURIComponent(filePath)}`;
        if (currentProject) {
            apiUrl += `&project_id=${encodeURIComponent(currentProject)}`;
        }
        
        const response = await fetch(apiUrl);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load file');
        }
        
        // Update file info
        document.getElementById('file-path-display').textContent = data.file_path;
        document.getElementById('file-size-display').textContent = formatFileSize(data.file_size);
        document.getElementById('file-type-display').textContent = data.extension || data.file_type;
        
        // Store file path and content in global variables for copy functionality
        currentFilePath = data.file_path;
        currentFileContent = data.content || '';
        
        if (data.line_count) {
            document.getElementById('file-lines-display').textContent = data.line_count.toLocaleString();
        } else {
            document.getElementById('file-lines-display').textContent = 'N/A';
        }
        
        // Display content or error
        loadingDiv.style.display = 'none';
        
        if (data.content !== null && data.content !== undefined) {
            // Show file content
            contentDiv.textContent = data.content;
            contentDiv.style.display = 'block';
            
            // Apply syntax highlighting if possible
            if (data.extension) {
                applySyntaxHighlighting(contentDiv, data.extension);
            }
        } else if (data.error) {
            // Show error message
            errorDiv.querySelector('p').textContent = data.error;
            errorDiv.style.display = 'block';
            
            // Disable content copy button when there's an error
            const contentBtn = document.getElementById('copy-file-content-btn');
            if (contentBtn) {
                contentBtn.disabled = true;
                contentBtn.style.opacity = '0.5';
                contentBtn.style.cursor = 'not-allowed';
            }
        }
        
        // Update modal title
        const fileName = filePath.split('/').pop() || filePath;
        document.getElementById('file-viewer-title').textContent = `File Viewer - ${fileName}`;
        
    } catch (error) {
        console.error('Error viewing file:', error);
        loadingDiv.style.display = 'none';
        errorDiv.querySelector('p').textContent = error.message || 'Failed to load file';
        errorDiv.style.display = 'block';
        
        // Clear global variables on error
        currentFilePath = '';
        currentFileContent = '';
        
        // Disable content copy button on error
        const contentBtn = document.getElementById('copy-file-content-btn');
        if (contentBtn) {
            contentBtn.disabled = true;
            contentBtn.style.opacity = '0.5';
            contentBtn.style.cursor = 'not-allowed';
        }
    }
}

// Close file viewer modal
// Global variables for file viewer
let currentFileContent = '';
let currentFilePath = '';

function closeFileViewer() {
    const modal = document.getElementById('file-viewer-modal');
    modal.style.display = 'none';
    
    // Clear content
    document.getElementById('file-content-display').textContent = '';
    document.getElementById('file-path-display').textContent = '';
    document.getElementById('file-size-display').textContent = '';
    document.getElementById('file-lines-display').textContent = '';
    document.getElementById('file-type-display').textContent = '';
    
    // Clear global variables
    currentFileContent = '';
    currentFilePath = '';
}

// Copy full file path to clipboard
async function copyFilePath() {
    if (!currentFilePath) {
        console.error('No file path to copy');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(currentFilePath);
        
        // Show success feedback
        const btn = document.getElementById('copy-file-path-btn');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<span style="font-size: 16px;">✅</span> Copied!';
        btn.classList.add('copy-success');
        
        // Reset button after animation
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.classList.remove('copy-success');
        }, 1000);
        
        console.log('File path copied to clipboard:', currentFilePath);
    } catch (err) {
        console.error('Failed to copy file path:', err);
        
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = currentFilePath;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            console.log('File path copied using fallback method');
            
            // Show success feedback
            const btn = document.getElementById('copy-file-path-btn');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<span style="font-size: 16px;">✅</span> Copied!';
            btn.classList.add('copy-success');
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('copy-success');
            }, 1000);
        } catch (fallbackErr) {
            console.error('Fallback copy failed:', fallbackErr);
            alert('Failed to copy file path. Please copy manually: ' + currentFilePath);
        } finally {
            document.body.removeChild(textArea);
        }
    }
}

// Copy file content to clipboard
async function copyFileContent() {
    if (!currentFileContent) {
        console.error('No file content to copy');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(currentFileContent);
        
        // Show success feedback
        const btn = document.getElementById('copy-file-content-btn');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<span style="font-size: 16px;">✅</span> Copied!';
        btn.classList.add('copy-success');
        
        // Reset button after animation
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.classList.remove('copy-success');
        }, 1000);
        
        console.log('File content copied to clipboard');
    } catch (err) {
        console.error('Failed to copy file content:', err);
        
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = currentFileContent;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            console.log('File content copied using fallback method');
            
            // Show success feedback
            const btn = document.getElementById('copy-file-content-btn');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<span style="font-size: 16px;">✅</span> Copied!';
            btn.classList.add('copy-success');
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('copy-success');
            }, 1000);
        } catch (fallbackErr) {
            console.error('Fallback copy failed:', fallbackErr);
            alert('Failed to copy file content. The file may be too large for clipboard.');
        } finally {
            document.body.removeChild(textArea);
        }
    }
}

// Add ESC key handler for file viewer modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const fileViewerModal = document.getElementById('file-viewer-modal');
        if (fileViewerModal && fileViewerModal.style.display === 'block') {
            closeFileViewer();
        }
    }
});

// Click outside to close file viewer modal
document.addEventListener('click', (e) => {
    const fileViewerModal = document.getElementById('file-viewer-modal');
    if (e.target === fileViewerModal) {
        closeFileViewer();
    }
});

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Basic syntax highlighting (optional enhancement)
function applySyntaxHighlighting(element, extension) {
    // This is a placeholder for syntax highlighting
    // You could integrate a library like Prism.js or highlight.js here
    // For now, just add a class based on file type
    const langMap = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.sh': 'bash',
        '.sql': 'sql'
    };
    
    const lang = langMap[extension.toLowerCase()];
    if (lang) {
        element.className = `language-${lang}`;
    }
}

// Make file links clickable
function makeFileLinksClickable(container) {
    // Find all file links in the container
    const fileLinks = container.querySelectorAll('.file-link, .file-path, .file-name');
    
    fileLinks.forEach(link => {
        if (!link.dataset.clickable) {
            link.dataset.clickable = 'true';
            link.style.cursor = 'pointer';
            link.style.color = '#007bff';
            link.style.textDecoration = 'underline';
            
            link.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const filePath = link.dataset.filePath || link.textContent.trim();
                if (filePath) {
                    viewFile(filePath);
                }
            });
            
            link.addEventListener('mouseenter', () => {
                link.style.color = '#0056b3';
            });
            
            link.addEventListener('mouseleave', () => {
                link.style.color = '#007bff';
            });
        }
    });
}

// No need for duplicate functions - the main functions handle everything now

// Logs data management
let currentLogsData = [];
let currentLogsOffset = 0;
let currentLogsLimit = 100;

// Load logs data
async function loadLogsData(isRefresh = false) {
    try {
        console.log('🔍 [LOGS DEBUG] Loading logs data for project:', currentProject);
        console.log('🔍 [LOGS DEBUG] isRefresh:', isRefresh);
        console.log('🔍 [LOGS DEBUG] Document title:', document.title);
        
        if (!currentProject) {
            console.log('🔍 [LOGS DEBUG] No project selected, showing message');
            document.getElementById('logs-content').innerHTML = 
                '<div class="loading-logs" style="text-align: center; padding: 40px; color: #666;">Select a project to view logs</div>';
            return;
        }
        
        // Show loading indicator
        if (!isRefresh) {
            document.getElementById('logs-content').innerHTML = 
                '<div class="loading-logs" style="text-align: center; padding: 40px; color: #666;">Loading logs...</div>';
        }
        
        // Get filter values
        const limit = parseInt(document.getElementById('logs-limit')?.value || 100);
        const levelFilter = document.getElementById('logs-level')?.value || '';
        
        // Build URL with parameters
        const params = new URLSearchParams({
            limit: limit.toString(),
            offset: currentLogsOffset.toString()
        });
        
        const url = `/api/projects/${currentProject}/logs?${params}`;
        console.log('🔍 [LOGS DEBUG] Fetching URL:', url);
        
        const response = await fetch(url);
        console.log('🔍 [LOGS DEBUG] Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const logsData = await response.json();
        console.log('🔍 [LOGS DEBUG] Loaded logs:', logsData.logs.length, 'total:', logsData.total);
        
        // Apply client-side level filtering if needed
        let filteredLogs = logsData.logs;
        if (levelFilter) {
            filteredLogs = logsData.logs.filter(log => log.level === levelFilter);
        }
        
        // Store data globally
        currentLogsData = filteredLogs;
        currentLogsLimit = limit;
        
        // Render logs
        console.log('🔍 [LOGS DEBUG] About to render logs:', filteredLogs.length, 'filtered logs');
        console.log('🔍 [LOGS DEBUG] Container element exists:', !!document.getElementById('logs-content'));
        renderLogs(filteredLogs, logsData);
        
        // Setup controls if not already done
        setupLogsControls();
        
    } catch (error) {
        console.error('Error loading logs:', error);
        document.getElementById('logs-content').innerHTML = 
            `<div class="error-state" style="text-align: center; padding: 40px; color: #e74c3c;">Error loading logs: ${error.message}</div>`;
    }
}

// Render logs in the display area
function renderLogs(logs, logsData) {
    console.log('🔍 [RENDER DEBUG] renderLogs called with:', logs ? logs.length : 'null', 'logs');
    const container = document.getElementById('logs-content');
    console.log('🔍 [RENDER DEBUG] Container found:', !!container);
    
    if (!logs || logs.length === 0) {
        console.log('🔍 [RENDER DEBUG] No logs to display, showing empty state');
        container.innerHTML = '<div class="empty-state" style="text-align: center; padding: 40px; color: #666;">No logs found for this project</div>';
        document.getElementById('logs-pagination').style.display = 'none';
        return;
    }
    
    let html = '<div class="logs-table" style="padding: 15px;">';
    
    // Header
    html += `
        <div class="logs-header" style="display: flex; padding: 10px 0; border-bottom: 2px solid #dee2e6; font-weight: bold; background: #f8f9fa; margin: -15px -15px 15px -15px; padding: 15px;">
            <div style="flex: 0 0 150px;">Date & Time</div>
            <div style="flex: 0 0 80px;">Level</div>
            <div style="flex: 0 0 120px;">Task ID</div>
            <div style="flex: 0 0 100px;">User</div>
            <div style="flex: 1;">Message</div>
        </div>
    `;
    
    // Log entries
    logs.forEach(log => {
        const formattedDate = formatDateWithTimezone(log.created_at);
        
        // Determine level color
        let levelColor = '#6c757d'; // Default gray
        switch(log.level) {
            case 'DEBUG': levelColor = '#17a2b8'; break;
            case 'INFO': levelColor = '#28a745'; break;
            case 'WARNING': levelColor = '#ffc107'; break;
            case 'ERROR': levelColor = '#dc3545'; break;
        }
        
        // Format task ID (clickable if exists)
        let taskIdDisplay = log.task_id || '-';
        if (log.task_id) {
            taskIdDisplay = `<a href="#" onclick="showTaskDetails('${log.task_id}')" style="color: #007bff; text-decoration: none;">${log.task_id}</a>`;
        }
        
        html += `
            <div class="log-entry" style="display: flex; padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 14px;">
                <div style="flex: 0 0 150px; color: #666; font-family: monospace; font-size: 12px;">${formattedDate}</div>
                <div style="flex: 0 0 80px;">
                    <span style="background: ${levelColor}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                        ${log.level || 'INFO'}
                    </span>
                </div>
                <div style="flex: 0 0 120px; font-family: monospace; font-size: 12px;">${taskIdDisplay}</div>
                <div style="flex: 0 0 100px; color: #666; font-size: 12px;">${log.user || '-'}</div>
                <div style="flex: 1; color: #333;">${log.message}</div>
            </div>
        `;
    });
    
    html += '</div>';
    
    console.log('🔍 [RENDER DEBUG] Setting innerHTML, HTML length:', html.length);
    container.innerHTML = html;
    console.log('🔍 [RENDER DEBUG] innerHTML set successfully');
    
    // Update pagination
    updateLogsPagination(logsData);
}

// Setup logs controls (refresh, clear, etc.)
function setupLogsControls() {
    // Refresh button
    const refreshBtn = document.getElementById('refresh-logs');
    if (refreshBtn && !refreshBtn.hasLogsListener) {
        refreshBtn.hasLogsListener = true;
        refreshBtn.addEventListener('click', () => {
            currentLogsOffset = 0; // Reset to first page
            loadLogsData(true);
        });
    }
    
    // Clear display button
    const clearBtn = document.getElementById('clear-logs-display');
    if (clearBtn && !clearBtn.hasLogsListener) {
        clearBtn.hasLogsListener = true;
        clearBtn.addEventListener('click', () => {
            document.getElementById('logs-content').innerHTML = 
                '<div class="loading-logs" style="text-align: center; padding: 40px; color: #666;">Logs cleared - click Refresh to reload</div>';
            document.getElementById('logs-pagination').style.display = 'none';
        });
    }
    
    // Limit dropdown
    const limitSelect = document.getElementById('logs-limit');
    if (limitSelect && !limitSelect.hasLogsListener) {
        limitSelect.hasLogsListener = true;
        limitSelect.addEventListener('change', () => {
            currentLogsOffset = 0; // Reset to first page
            loadLogsData();
        });
    }
    
    // Level filter
    const levelSelect = document.getElementById('logs-level');
    if (levelSelect && !levelSelect.hasLogsListener) {
        levelSelect.hasLogsListener = true;
        levelSelect.addEventListener('change', () => {
            loadLogsData();
        });
    }
}

// Setup timezone settings
function setupTimezoneSettings() {
    // Display current browser timezone
    const browserTimezoneElement = document.getElementById('browser-timezone');
    if (browserTimezoneElement) {
        browserTimezoneElement.textContent = Intl.DateTimeFormat().resolvedOptions().timeZone;
    }
    
    // Set current timezone in select
    const timezoneSelect = document.getElementById('timezone-select');
    if (timezoneSelect) {
        // Set the current timezone
        timezoneSelect.value = userTimezone;
        
        // If current timezone is not in the list, add it
        if (!Array.from(timezoneSelect.options).some(option => option.value === userTimezone)) {
            const option = document.createElement('option');
            option.value = userTimezone;
            option.textContent = userTimezone + ' (Current)';
            timezoneSelect.insertBefore(option, timezoneSelect.firstChild);
            timezoneSelect.value = userTimezone;
        }
    }
    
    // Save timezone button
    const saveTimezoneBtn = document.getElementById('save-timezone');
    if (saveTimezoneBtn) {
        saveTimezoneBtn.addEventListener('click', async () => {
            const selectedTimezone = timezoneSelect.value;
            const statusDiv = document.getElementById('timezone-save-status');
            
            try {
                // Save to localStorage
                localStorage.setItem('userTimezone', selectedTimezone);
                userTimezone = selectedTimezone;
                
                // Show success message
                statusDiv.style.display = 'block';
                statusDiv.style.color = '#28a745';
                statusDiv.textContent = '✅ Timezone saved successfully! Refreshing logs...';
                
                // Reload logs data if on logs tab
                const activeTab = document.querySelector('.tab-button.active');
                if (activeTab && activeTab.getAttribute('data-tab') === 'logs') {
                    loadLogsData();
                }
                
                // Also update any visible timestamps in other tabs
                updateAllTimestamps();
                
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 3000);
                
            } catch (error) {
                statusDiv.style.display = 'block';
                statusDiv.style.color = '#dc3545';
                statusDiv.textContent = '❌ Error saving timezone: ' + error.message;
            }
        });
    }
}

// Update all visible timestamps with new timezone
function updateAllTimestamps() {
    // Update task dates if visible
    const taskCards = document.querySelectorAll('.task-created-at, .task-updated-at');
    taskCards.forEach(element => {
        const dateStr = element.getAttribute('data-date');
        if (dateStr) {
            element.textContent = formatDateWithTimezone(dateStr);
        }
    });
    
    // Update any other timestamps in the UI
    const timestamps = document.querySelectorAll('[data-timestamp]');
    timestamps.forEach(element => {
        const dateStr = element.getAttribute('data-timestamp');
        if (dateStr) {
            element.textContent = formatDateWithTimezone(dateStr);
        }
    });
}

// Update logs pagination
function updateLogsPagination(logsData) {
    const pagination = document.getElementById('logs-pagination');
    const prevBtn = document.getElementById('logs-prev');
    const nextBtn = document.getElementById('logs-next');
    const pageInfo = document.getElementById('logs-page-info');
    
    if (!pagination || !logsData) return;
    
    const total = logsData.total || 0;
    const limit = logsData.limit || currentLogsLimit;
    const offset = logsData.offset || currentLogsOffset;
    
    const currentPage = Math.floor(offset / limit) + 1;
    const totalPages = Math.ceil(total / limit);
    
    // Show pagination if there are multiple pages
    if (totalPages > 1) {
        pagination.style.display = 'block';
        
        // Update page info
        pageInfo.textContent = `Page ${currentPage} of ${totalPages} (${total} total logs)`;
        
        // Update button states
        prevBtn.disabled = currentPage <= 1;
        nextBtn.disabled = currentPage >= totalPages;
        
        // Setup button listeners
        if (!prevBtn.hasLogsListener) {
            prevBtn.hasLogsListener = true;
            prevBtn.addEventListener('click', () => {
                if (currentLogsOffset > 0) {
                    currentLogsOffset = Math.max(0, currentLogsOffset - limit);
                    loadLogsData();
                }
            });
        }
        
        if (!nextBtn.hasLogsListener) {
            nextBtn.hasLogsListener = true;
            nextBtn.addEventListener('click', () => {
                if (currentLogsOffset + limit < total) {
                    currentLogsOffset += limit;
                    loadLogsData();
                }
            });
        }
    } else {
        pagination.style.display = 'none';
    }
}

// Load current tab data
function loadCurrentTabData() {
    const activeTab = document.querySelector('.tab-button.active');
    if (activeTab && currentProject) {
        const tabName = activeTab.getAttribute('data-tab');
        if (tabName === 'tasks') {
            loadTasksData();
        } else if (tabName === 'team') {
            loadTeamData();
        } else if (tabName === 'logs') {
            loadLogsData();
        } else if (tabName === 'matrix') {
            loadMatrixData();
        }
    }
}

// Load project statistics
async function loadProjectStatistics() {
    console.log('🔍 [STATS DEBUG] Loading project statistics for:', currentProject);
    
    const container = document.getElementById('project-statistics-content');
    if (!container) {
        console.log('🔍 [STATS DEBUG] Container not found: project-statistics-content');
        return;
    }
    
    if (!currentProject) {
        container.innerHTML = '<p style="color: #666;">Select a project to view statistics</p>';
        return;
    }
    
    container.innerHTML = '<p class="loading">Loading project statistics...</p>';
    
    try {
        const url = `/api/projects/${currentProject}/statistics`;
        console.log('🔍 [STATS DEBUG] Fetching URL:', url);
        const response = await fetch(url);
        console.log('🔍 [STATS DEBUG] Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const stats = await response.json();
        console.log('🔍 [STATS DEBUG] Statistics loaded:', stats);
        
        // Format dates
        const formatDate = (dateStr) => {
            if (!dateStr) return 'Not available';
            return formatDateWithTimezone(dateStr);
        };
        
        // Calculate project duration
        const calculateDuration = (start, end) => {
            if (!start || !end) return 'Ongoing';
            try {
                const startDate = new Date(start);
                const endDate = new Date(end);
                const diffMs = endDate - startDate;
                const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
                
                if (diffDays === 0) return 'Same day';
                if (diffDays === 1) return '1 day';
                if (diffDays < 30) return `${diffDays} days`;
                if (diffDays < 365) {
                    const months = Math.floor(diffDays / 30);
                    return `${months} month${months > 1 ? 's' : ''} (${diffDays} days)`;
                } else {
                    const years = Math.floor(diffDays / 365);
                    const months = Math.floor((diffDays % 365) / 30);
                    return `${years} year${years > 1 ? 's' : ''} ${months} month${months > 1 ? 's' : ''} (${diffDays} days)`;
                }
            } catch (e) {
                return 'Unknown';
            }
        };
        
        // Build task status summary
        let taskStatusHtml = '';
        const statusColors = {
            'TODO': '#6c757d',
            'READY': '#17a2b8', 
            'DOING': '#ffc107',
            'TESTING': '#fd7e14',
            'DONE': '#28a745',
            'PENDING': '#6f42c1',
            'CANCELED': '#dc3545'
        };
        
        for (const [status, count] of Object.entries(stats.task_status_counts)) {
            const color = statusColors[status] || '#6c757d';
            taskStatusHtml += `
                <span style="display: inline-block; margin: 2px 5px; padding: 4px 8px; background: ${color}; color: white; border-radius: 12px; font-size: 12px; font-weight: bold;">
                    ${status}: ${count}
                </span>
            `;
        }
        
        const duration = calculateDuration(stats.project_created_at, stats.latest_log_at);
        const isActive = stats.period.active;
        
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                <!-- Project Period -->
                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h4 style="margin-top: 0; color: #495057; display: flex; align-items: center;">
                        📅 Project Period
                        <span style="margin-left: 10px; padding: 2px 8px; background: ${isActive ? '#28a745' : '#6c757d'}; color: white; border-radius: 12px; font-size: 11px;">
                            ${isActive ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                    </h4>
                    <div style="margin-bottom: 10px;">
                        <strong>Start:</strong> ${formatDate(stats.project_created_at)}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Latest Activity:</strong> ${formatDate(stats.latest_log_at)}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Duration:</strong> ${duration}
                    </div>
                </div>
                
                <!-- Task Summary -->
                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h4 style="margin-top: 0; color: #495057;">📋 Task Summary</h4>
                    <div style="margin-bottom: 15px;">
                        <strong>Total Tasks:</strong> ${stats.total_tasks}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>By Status:</strong>
                    </div>
                    <div>
                        ${taskStatusHtml || '<span style="color: #666;">No tasks found</span>'}
                    </div>
                </div>
                
                <!-- Activity Summary -->
                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h4 style="margin-top: 0; color: #495057;">📝 Activity Summary</h4>
                    <div style="margin-bottom: 10px;">
                        <strong>Total Log Entries:</strong> ${stats.total_logs}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Project ID:</strong> <code>${stats.project_id}</code>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Last Updated:</strong> ${formatDate(stats.latest_log_at) || 'No activity'}
                    </div>
                </div>
            </div>
            
            <!-- Quick Actions -->
            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <h4 style="margin-top: 0; color: #495057;">🔗 Quick Actions</h4>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button onclick="document.querySelector('[data-tab=\"logs\"]').click()" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        📝 View Project Logs
                    </button>
                    <button onclick="document.querySelector('[data-tab=\"tasks\"]').click()" style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        📋 View Tasks
                    </button>
                    <button onclick="document.querySelector('[data-tab=\"matrix\"]').click()" style="padding: 8px 16px; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        🔗 View Traceability Matrix
                    </button>
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading project statistics:', error);
        container.innerHTML = `<p style="color: #e74c3c;">Error loading statistics: ${error.message}</p>`;
    }
}

// Export functions
window.showMemberDetails = showMemberDetails;
window.showTaskDetails = showTaskDetails;
window.updateTaskStatus = updateTaskStatus;
window.updateTaskAssignee = updateTaskAssignee;
window.loadSettings = loadSettings;
window.loadLogsData = loadLogsData;
window.loadProjectStatistics = loadProjectStatistics;
window.viewFile = viewFile;
window.closeFileViewer = closeFileViewer;
window.showFileTaskRelation = showFileTaskRelation;