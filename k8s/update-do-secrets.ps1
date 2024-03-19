$envFilePath = './env.secrets'
$secretName = 'jarvis-secrets'

# Read each line from the .env file
$lines = Get-Content $envFilePath

# Create the secret (delete if exists)
kubectl delete secret $secretName --ignore-not-found
$arguments = @()
foreach ($line in $lines) {
    if (-not [string]::IsNullOrWhiteSpace($line)) {
        $keyValue = $line -split '=',2
        $key = $keyValue[0].Trim()
        $value = $keyValue[1].Trim()
        $arguments += "--from-literal=$key=$value"
    }
}
kubectl create secret generic $secretName @arguments