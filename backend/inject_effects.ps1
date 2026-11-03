$files = @(
  "D:\Claude\crossbot-ai\backend\app\static\home.html",
  "D:\Claude\crossbot-ai\backend\app\static\gpsr-check.html",
  "D:\Claude\crossbot-ai\backend\app\static\gpsr-check-pl.html",
  "D:\Claude\crossbot-ai\backend\app\static\gpsr-check-ro.html",
  "D:\Claude\crossbot-ai\backend\app\static\pricing.html",
  "D:\Claude\crossbot-ai\backend\app\static\rules.html",
  "D:\Claude\crossbot-ai\backend\app\static\skills.html"
)
foreach($f in $files){
  $content = [IO.File]::ReadAllText($f)
  if($content -notmatch "effects.css"){
    $content = $content.Replace("</head>", '  <link rel="stylesheet" href="/effects.css">' + "`n</head>")
  }
  if($content -notmatch "effects.js"){
    $content = $content.Replace("</body>", '  <script src="/effects.js"></script>' + "`n</body>")
  }
  [IO.File]::WriteAllText($f, $content, [Text.UTF8Encoding]::new($false))
  Write-Host "OK: $f"
}
