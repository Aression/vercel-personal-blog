# 生成 og:image 社交预览图（1200x630 PNG），Windows 侧 GDI+ 绘制。
# 由 tools/gen_og.py 调用：读 JSON 任务清单（UTF-8），避免中文走命令行参数的编码问题。
param([Parameter(Mandatory = $true)][string]$Jobs)

Add-Type -AssemblyName System.Drawing

$W = 1200; $H = 630
$list = Get-Content -Raw -Encoding UTF8 $Jobs | ConvertFrom-Json

$ink = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(17, 17, 17))
$soft = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(70, 70, 70))
$mute = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(130, 130, 130))
$lineP = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(226, 226, 226)), 2

$fTitle = New-Object System.Drawing.Font('Microsoft YaHei', 44, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fKick = New-Object System.Drawing.Font('Microsoft YaHei', 20, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$fFoot = New-Object System.Drawing.Font('Microsoft YaHei', 22, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$fMark = New-Object System.Drawing.Font('Microsoft YaHei', 26, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)

$made = 0
foreach ($job in $list) {
    $bmp = New-Object System.Drawing.Bitmap $W, $H
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
    $g.Clear([System.Drawing.Color]::White)

    # 左侧黑条 + 底部细线
    $g.FillRectangle($ink, 0, 0, 12, $H)
    $g.DrawLine($lineP, 96, 520, 1104, 520)

    # 右上角站点标识
    $g.DrawString($job.brand, $fMark, $ink, 912, 74)
    $g.DrawString($job.domain, $fKick, $mute, 912, 112)

    # 顶部 kicker（日期 / 分类）
    if ($job.kicker) {
        $g.DrawString($job.kicker, $fKick, $mute, 96, 96)
    }

    # 标题：优先在标点处断行（中文不该切断语义单元），不行再按字宽硬折
    $maxW = 800
    $lines = New-Object System.Collections.ArrayList
    $title = $job.title

    $puncts = @('，', '、', '；', '：', '！', '？', '—', '·', ',', ' ')
    $best = $null
    foreach ($p in $puncts) {
        $idx = $title.IndexOf($p)
        while ($idx -gt 0 -and $idx -lt $title.Length - 1) {
            $a = $title.Substring(0, $idx + 1).Trim()
            $b = $title.Substring($idx + 1).Trim()
            if ($a.Length -gt 0 -and $b.Length -gt 0) {
                $wa = $g.MeasureString($a, $fTitle).Width
                $wb = $g.MeasureString($b, $fTitle).Width
                if ($wa -le $maxW -and $wb -le $maxW) {
                    $ratio = [Math]::Min($wa, $wb) / [Math]::Max($wa, $wb)
                    if ($ratio -ge 0.45 -and ($null -eq $best -or $ratio -gt $best.ratio)) {
                        $best = @{ a = $a; b = $b; ratio = $ratio }
                    }
                }
            }
            $idx = $title.IndexOf($p, $idx + 1)
        }
    }

    if ($null -ne $best) {
        [void]$lines.Add($best.a)
        [void]$lines.Add($best.b)
    }
    else {
        $cur = ''
        foreach ($ch in $title.ToCharArray()) {
            $try = $cur + [string]$ch
            $w = $g.MeasureString($try, $fTitle).Width
            if ($w -gt $maxW -and $cur.Length -gt 0) {
                [void]$lines.Add($cur)
                $cur = [string]$ch
            }
            else {
                $cur = $try
            }
        }
        if ($cur.Length -gt 0) { [void]$lines.Add($cur) }
        # 避免末行孤字：末行太短就从上一行末尾搬字下来
        if ($lines.Count -ge 2) {
            $total = 0
            foreach ($ln in $lines) { $total += $ln.Length }
            $avg = [int]($total / $lines.Count)
            $minLen = [Math]::Max(4, [int]($avg * 0.45))
            $last = $lines.Count - 1
            while ($lines[$last].Length -lt $minLen -and $lines[$last - 1].Length -gt $minLen + 2) {
                $prev = $lines[$last - 1]
                $move = $prev.Substring($prev.Length - 1)
                $lines[$last - 1] = $prev.Substring(0, $prev.Length - 1)
                $lines[$last] = $move + $lines[$last]
            }
        }
    }
    if ($lines.Count -gt 4) {
        $lines = $lines.GetRange(0, 4)
        $lines[3] = $lines[3] + '…'
    }

    $y = 178
    foreach ($ln in $lines) {
        $g.DrawString($ln, $fTitle, $ink, 96, $y)
        $y += 68
    }

    # 底部信息
    if ($job.foot) { $g.DrawString($job.foot, $fFoot, $soft, 96, 548) }
    if ($job.tags) { $g.DrawString($job.tags, $fKick, $mute, 96, 590) }

    $bmp.Save($job.out, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Output ("ok " + $job.out)
    $made++
}
Write-Output ("generated " + $made)
