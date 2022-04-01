// window.addEventListener('load', () => {

    document.querySelector("#new-task").addEventListener('click', () => {
        const newTaskForm = document.getElementById('new-task-form');
        const collapseForm = new bootstrap.Collapse(newTaskForm)
        collapseForm.toggle();
    });

    // document.querySelector("#new-workflow").addEventListener('click', () => {
    //     const newWorkflowForm = document.getElementById('new-workflow-form');
    //     const collapseForm = new bootstrap.Collapse(newWorkflowForm)
    //     collapseForm.toggle();
    // });

    // let cp_select = document.querySelector('.container.workflows #processors');
    // if (cp_select.length > 0) {
    //     cp_select.multiSelect({
    //         "keepOrder": true
    //     });
    // }

// });
