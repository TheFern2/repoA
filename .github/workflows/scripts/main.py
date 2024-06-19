import requests
import json
import os
import sys
import zipfile

TOKEN = os.getenv('MY_TOKEN')

# def trigger_workflow(repo_owner, repo_name, token, tag):
#     url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/dispatches"
#     headers = {
#         "Accept": "application/vnd.github.everest-preview+json",
#         "Authorization": f"Bearer {token}"
#     }
#     payload = {
#         "event_type": "trigger-event",
#         "client_payload": {
#             "version_tag": tag
#         }
#     }
#     response = requests.post(url, headers=headers, data=json.dumps(payload))
#     if response.status_code == 204:
#         print("Workflow triggered successfully!")
#     else:
#         print("Failed to trigger workflow:", response.status_code, response.text)

def download_release_artifact(repo_owner, repo_name, token, tag):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/tags/{tag}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Failed to get release information:", response.status_code, response.text)
        return None

    release_data = response.json()
    asset_url = release_data['assets'][0]['url']
    asset_name = release_data['assets'][0]['name']

    headers.update({"Accept": "application/octet-stream"})
    response = requests.get(asset_url, headers=headers, stream=True)
    if response.status_code != 200:
        print("Failed to download the release asset:", response.status_code, response.text)
        return None

    with open(asset_name, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return asset_name

def extract_docker_compose(artifact_name):
    with zipfile.ZipFile(artifact_name, 'r') as zip_ref:
        zip_ref.extractall('artifact_contents')

    src_file = os.path.join('artifact_contents', 'docker-compose.yml')
    dest_dir = 'docker'
    os.makedirs(dest_dir, exist_ok=True)
    dest_file = os.path.join(dest_dir, 'docker-compose.yml')

    if os.path.isfile(src_file):
        os.rename(src_file, dest_file)
        return dest_file
    else:
        print("docker-compose.yml not found in the artifact.")
        return None

def commit_and_push_file(repo_owner, repo_name, token, file_path, tag):
    from git import Repo

    repo_url = f"https://{token}@github.com/{repo_owner}/{repo_name}.git"
    repo_dir = 'repoA_clone'
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir)

    repo = Repo.clone_from(repo_url, repo_dir)
    repo.git.add(file_path)
    repo.index.commit(f"Add docker-compose.yml from {repo_name} release {tag}")
    origin = repo.remote(name='origin')
    origin.push()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <version_tag>")
        sys.exit(1)

    version_tag = sys.argv[1]
    repo_a_owner = "TheFern2"
    repo_a_name = "repoA"
    repo_b_owner = "TheFern2"
    repo_b_name = "repoB"

    # trigger_workflow(repo_a_owner, repo_a_name, TOKEN, version_tag)
    artifact_name = download_release_artifact(repo_b_owner, repo_b_name, TOKEN, version_tag)
    if artifact_name:
        extracted_file = extract_docker_compose(artifact_name)
        if extracted_file:
            commit_and_push_file(repo_a_owner, repo_a_name, TOKEN, extracted_file, version_tag)
