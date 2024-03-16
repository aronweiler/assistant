## Example:
# .\build_docker.ps1 -serviceName 'jarvis-worker-document-processing' -overrideVersion '1.1'

param (
    [string]$serviceName,
    [string]$overrideVersion
)

# Define build contexts and Dockerfiles for each service
$services = @{
    'jarvis-database'                   = @{ Context = '.'; Dockerfile = 'src/database/Dockerfile' }
    'jarvis-ui'                         = @{ Context = '.'; Dockerfile = 'src/ui/Dockerfile' }
    'jarvis-ui-react'                   = @{ Context = './src/react-ui'; Dockerfile = 'Dockerfile' }
    'jarvis-api-user'                   = @{ Context = '.'; Dockerfile = './src/api/user/Dockerfile' }
    'jarvis-worker-document-processing' = @{ Context = '.'; Dockerfile = './src/workers/document_processing/Dockerfile' }
}

if (-not $services.ContainsKey($serviceName)) {
    Write-Host "Service name '
$serviceName' is not recognized."
    exit
}

# Read the current version from version.txt
$currentVersion = Get-Content -Path version.txt
Write-Host "Current version is $currentVersion"

# If an override version is provided, use it; otherwise, increment the minor version
if ($overrideVersion) {
    $newVersion = $overrideVersion
    Write-Host "Overriding version to $newVersion"
}
else {
    $versionParts = $currentVersion.Split('.')
    $majorVersion = [int]$versionParts[0]
    $minorVersion = [int]$versionParts[1] + 1
    $newVersion = "$majorVersion.$minorVersion"
    Write-Host "Incrementing version to $newVersion"

    # Write the new version back to version.txt
    $newVersion | Set-Content -Path version.txt
}

$context = $services[$serviceName].Context
$dockerfile = $services[$serviceName].Dockerfile
$tagVersioned = "aronweiler/assistant:$newVersion-$serviceName"
$tagLatest = "aronweiler/assistant:latest-$serviceName"

Write-Host "Building $serviceName with tags $tagVersioned and $tagLatest"
docker build -t $tagVersioned -t $tagLatest -f $dockerfile $context
if ($LASTEXITCODE -eq 0) {
    Write-Host "$serviceName build succeeded"
    # Push the Docker images -- uncomment for production
    docker push $tagVersioned
    docker push $tagLatest
}
else {
    Write-Host "$serviceName build failed"
}