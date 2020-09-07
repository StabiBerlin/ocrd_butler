from flask_restx import Resource
from ocrd_butler.api_v1.restx import api_v1


processor_namespace = api_v1.namespace("processor", description="")

@processor_namespace.route("/processor")
class Processor(Resource):
    """
    
    """

    @api_v1.doc(responses={200: 'List all processors'})
    def get(self):
        """
        List all processors.
        """



@processor_namespace.route("/processor/<string:executable>")
class Processor(Resource):
    """
    
    """

    @api_v1.doc(responses={200: 'Get this processor', 404: 'Processor not available'})
    def get(self, executable):
        """
        Get this processor.
        """

    @api_v1.doc(responses={200: 'Return the ProcessorJob running this ProcessorCall'})
    def post(self, executable):
        """
        Return the ProcessorJob running this ProcessorCall.
        """



@processor_namespace.route("/processor/<string:executable>/<string:job_id>")
class Processor(Resource):
    """
    
    """

    @api_v1.doc(responses={200: 'Return ProcessorJob', 404: 'ProcessorJob not found'})
    def get(self, executable, job_id):
        """
        Return ProcessorJob.
        """



@processor_namespace.route("/processor/<string:executable>/<string:job_id>")
class Processor(Resource):
    """
    
    """

    @api_v1.doc(responses={200: 'Return Log', 404: 'ProcessorJob not found'})
    def get(self, executable, job_id):
        """
        Return Log.
        """

    @api_v1.doc(responses={200: 'Return Log', 404: 'ProcessorJob not found'})
    def post(self, executable, job_id):
        """
        Return Log.
        """


workflow_namespace = api_v1.namespace("workflow", description="Processing of OCRD-WF")

@workflow_namespace.route("/workflow")
class Workflow(Resource):
    """
    Processing of OCRD-WF
    """

    @api_v1.doc(responses={200: 'Created a new OCR-D workflow'})
    def post(self):
        """
        Created a new OCR-D workflow.
        """



@workflow_namespace.route("/workflow/<string:workflow_id>")
class Workflow(Resource):
    """
    Processing of OCRD-WF
    """

    @api_v1.doc(responses={200: 'Created a new OCR-D workflow'})
    def put(self, workflow_id):
        """
        Created a new OCR-D workflow.
        """

    @api_v1.doc(responses={200: 'Return ProcessorJob', 404: 'Workflow not available'})
    def get(self, workflow_id):
        """
        Return ProcessorJob.
        """

    @api_v1.doc(responses={200: 'Return WorkflowJob'})
    def post(self, workflow_id):
        """
        Return WorkflowJob.
        """



@workflow_namespace.route("/workflow/<string:workflow_id>/<string:job_id>")
class Workflow(Resource):
    """
    Processing of OCRD-WF
    """

    @api_v1.doc(responses={200: 'Found WorkflowJob', 404: 'WorkflowJob not found'})
    def get(self, workflow_id, job_id):
        """
        Found WorkflowJob.
        """


workspace_namespace = api_v1.namespace("workspace", description="mets.xml-indexed BagIt container")

@workspace_namespace.route("/workspace")
class Workspace(Resource):
    """
    mets.xml-indexed BagIt container
    """

    @api_v1.doc(responses={200: 'successful operation'})
    def get(self):
        """
        successful operation.
        """

    @api_v1.doc(responses={201: 'Workspace created'})
    def post(self):
        """
        """

    @api_v1.doc(responses={200: 'Successfully replaced workspace'})
    def put(self):
        """
        """



@workspace_namespace.route("/workspace/<string:workspace_id>")
class Workspace(Resource):
    """
    mets.xml-indexed BagIt container
    """

    @api_v1.doc(responses={200: 'Workspace found', 404: 'Workspace not found', 410: 'Workspace deleted'})
    def get(self, workspace_id):
        """
        Workspace found.
        """

    @api_v1.doc(responses={200: 'Workspace deleted', 404: 'Workspace not found', 410: 'Workspace deleted'})
    def delete(self, workspace_id):
        """
        Workspace deleted.
        """


discovery_namespace = api_v1.namespace("discovery", description="Discovery of capabilities of a server")

@discovery_namespace.route("/discovery")
class Discovery(Resource):
    """
    Discovery of capabilities of a server
    """

    @api_v1.doc(responses={200: 'Return DiscoveryResponse'})
    def get(self):
        """
        Return DiscoveryResponse.
        """

