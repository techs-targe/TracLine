// View Mode Switcher functionality
console.log("Loading View Mode Switcher JS");

// Global function for view mode switching that can be accessed from HTML
function changeViewMode(mode) {
    console.log("changeViewMode called with mode:", mode);
    
    // Update active button appearance
    const buttons = document.querySelectorAll('.view-mode-btn');
    buttons.forEach(btn => {
        if (btn.dataset.mode === mode) {
            btn.classList.add('active');
            btn.style.background = '#4CAF50';
            btn.style.color = 'white';
        } else {
            btn.classList.remove('active');
            btn.style.background = '#e0e0e0';
            btn.style.color = 'black';
        }
    });
    
    // Update view mode class on hierarchy container
    const hierarchyContainer = document.querySelector('.hierarchy-container');
    if (hierarchyContainer) {
        hierarchyContainer.className = `hierarchy-container hierarchy-${mode}`;
    } else {
        console.error("Hierarchy container not found");
    }
    
    // Store current mode in global app state if app.js is loaded
    if (typeof window.currentViewMode !== 'undefined') {
        window.currentViewMode = mode;
        
        // Reload data if loadTeamData function exists
        if (typeof window.loadTeamData === 'function') {
            window.loadTeamData();
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log("View Mode Switcher initializing");
    
    // Make function globally available
    window.changeViewMode = changeViewMode;
    
    // Apply view mode directly if needed
    const hierarchyContainer = document.querySelector('.hierarchy-container');
    if (hierarchyContainer) {
        hierarchyContainer.className = 'hierarchy-container hierarchy-pyramid';
    }
});