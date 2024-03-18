param (
    [string]$overrideVersion
)

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
    # Special case for the UI, which has its own version.txt
    $newVersion | Set-Content -Path ./src/ui/app/version.txt
}

# Define build contexts and Dockerfiles for each service
$services = @{
    'jarvis-database' = @{ Context = '.'; Dockerfile = 'src/database/Dockerfile' }
    'jarvis-ui' = @{ Context = '.'; Dockerfile = 'src/ui/Dockerfile' }
    'jarvis-ui-react' = @{ Context = './src/react-ui'; Dockerfile = 'Dockerfile' }
    'jarvis-api-user' = @{ Context = '.'; Dockerfile = './src/api/user/Dockerfile' }
    'jarvis-worker-document-processing' = @{ Context = '.'; Dockerfile = './src/workers/document_processing/Dockerfile' }
}

foreach ($service in $services.Keys) {
    $context = $services[$service].Context
    $dockerfile = $services[$service].Dockerfile
    $tag = "aronweiler/assistant:$newVersion-$service"

    Write-Host "Building $service with tag $tag"
    docker build -t $tag -f $dockerfile $context
    if ($LASTEXITCODE -eq 0) {
        Write-Host "$service build succeeded"
        # Push the Docker images -- uncomment for production
        # docker push $tag
    }
    else {
        Write-Host "$service build failed"
    }
}