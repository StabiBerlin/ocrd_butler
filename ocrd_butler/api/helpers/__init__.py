from ocrd_butler.database.models import Workflow


def add_workflow_processor(workflow: Workflow, processor: dict):
    workflow.processors = workflow.processors + [processor]
    return workflow.save()
