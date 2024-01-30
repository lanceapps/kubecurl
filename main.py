from flask import Flask, render_template, request, redirect, url_for
from kubernetes import client, config
import subprocess
import os

app = Flask(__name__)

# Load in-cluster Kubernetes config
config.load_incluster_config()

# Kubernetes API client
v1 = client.CoreV1Api()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/pods')
def pods():
    # Query Kubernetes API for pod information
    pod_list = v1.list_pod_for_all_namespaces().items

    # Format pod information as HTML table with clickable links
    table_html = '<table class="table table-hover">'
    table_html += '<tr><th>Namespace</th><th>Name</th><th>IP</th><th>Status</th><th>Container Port</th><th>Action</th></tr>'
    for pod in pod_list:
        # Get container port (assuming the first container is considered)
        container_port = pod.spec.containers[0].ports[0].container_port if pod.spec.containers and pod.spec.containers[0].ports else "N/A"

        # Generate clickable link to details page for each pod
        details_url = url_for('pod_details', namespace=pod.metadata.namespace, name=pod.metadata.name)

        # Add pod information to table rows
        table_html += f'<tr><td>{pod.metadata.namespace}</td><td>{pod.metadata.name}</td><td>{pod.status.pod_ip}</td><td>{pod.status.phase}</td><td>{container_port}</td><td><a href="{details_url}">View</a></td></tr>'
    table_html += '</table>'

    # Render HTML template with the table
    return render_template('pods.html', table_html=table_html)


@app.route('/pods/<namespace>/<name>')
def pod_details(namespace, name):
    # Query Kubernetes API for details of the specified pod
    pod = v1.read_namespaced_pod(name, namespace)

    # Get container port (assuming the first container is considered)
    container_port = pod.spec.containers[0].ports[0].container_port if pod.spec.containers and pod.spec.containers[0].ports else "N/A"

    # Render HTML template with pod details and container port
    return render_template('pod_details.html', pod=pod, container_port=container_port)


@app.route('/send_request', methods=['POST'])
def send_request():
    # Extract pod name and namespace from URL parameters
    pod_name = request.args.get('name')
    namespace = request.args.get('namespace')

    # Query Kubernetes API for details of the specified pod
    pod = v1.read_namespaced_pod(pod_name, namespace)

    # Extract container IP address and port
    container_ip = pod.status.pod_ip
    container_port = pod.spec.containers[0].ports[0].container_port

    # Extract URI path from form submission
    uri = request.form['uri']

    # Construct full URL
    full_url = f'http://{container_ip}:{container_port}{uri}'

    # Construct curl command
    curl_command = f'curl -s -X GET {full_url}'

    # Execute curl command and capture output
    try:
        process = subprocess.Popen(curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        response = stdout.decode('utf-8')
        if stderr:
            response += f"\nError occurred: {stderr.decode('utf-8')}"
    except Exception as e:
        response = f"Error occurred: {str(e)}"

    # Return the response to the client
    return response


if __name__ == '__main__':
    app.run(debug=True)
