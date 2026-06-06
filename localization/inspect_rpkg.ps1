# inspect_rpkg.ps1
# Parse header RPKGv2 (2KPR) theo dung format chinh thuc:
# https://glaciermodding.org/docs/glacier2/formats/rpkg
#
# Chay: powershell -ExecutionPolicy Bypass -File inspect_rpkg.ps1
# Hoac: powershell -ExecutionPolicy Bypass -File inspect_rpkg.ps1 -RpkgPath "path\to\chunk1.rpkg"

param(
    [string]$RpkgPath = "d:\Games\007 First Light\Runtime\chunk0.rpkg"
)

Write-Host "Parsing: $RpkgPath" -ForegroundColor Cyan
$fileSize = (Get-Item $RpkgPath).Length
Write-Host ("Size: {0:N0} bytes  ({1:N2} GB)" -f $fileSize, ($fileSize / 1GB))
Write-Host ""

$fs = [System.IO.File]::OpenRead($RpkgPath)
$br = New-Object System.IO.BinaryReader($fs)

# ================================================================
# HEADER FORMAT (2KPR / RPKGv2):
#   [4]   magic          "2KPR"
#   [4]   unknown        uint32 (always 0x1)
#   [1]   chunk_number   uint8
#   [1]   chunk_type     uint8  (0=standard, 1=addon)
#   [1]   chunk_patch    uint8
#   [16]  language_code  char[16]  (e.g. "xx\0...")
#   [4]   resource_count uint32
#   [4]   data_table_sz  uint32
#   [4]   patch_del_cnt  uint32  (only patch files)
# ================================================================

$magic       = [System.Text.Encoding]::ASCII.GetString($br.ReadBytes(4))  # offset 0
$unknown     = $br.ReadUInt32()   # offset 4
$chunkNum    = $br.ReadByte()     # offset 8
$chunkType   = $br.ReadByte()     # offset 9
$chunkPatch  = $br.ReadByte()     # offset 10
$langCode    = [System.Text.Encoding]::ASCII.GetString($br.ReadBytes(16)) -replace "`0","" # offset 11
$resCount    = $br.ReadUInt32()   # offset 27
$dataTableSz = $br.ReadUInt32()   # offset 31
# patch_del_cnt only exists in patch files — read anyway, check later
$patchDelCnt = $br.ReadUInt32()   # offset 35

Write-Host ("Magic:          {0}" -f $magic)
Write-Host ("Unknown:        0x{0:X8}" -f $unknown)
Write-Host ("Chunk number:   {0}" -f $chunkNum)
Write-Host ("Chunk type:     {0} ({1})" -f $chunkType, $(if ($chunkType -eq 0) {"standard"} else {"addon"}))
Write-Host ("Chunk patch:    {0}" -f $chunkPatch)
Write-Host ("Language code:  '{0}'" -f $langCode)
Write-Host ("Resource count: {0:N0}" -f $resCount)
Write-Host ("Data table sz:  {0:N0}" -f $dataTableSz)
Write-Host ("Patch del cnt:  {0:N0}" -f $patchDelCnt)
Write-Host ""

if ($magic -ne "2KPR" -and $magic -ne "GKPR") {
    Write-Host "[!] Magic khong hop le." -ForegroundColor Red
    $br.Close(); $fs.Close(); exit
}

if ($resCount -eq 0 -or $resCount -gt 2000000) {
    Write-Host "[!] resource_count = $resCount, co ve khong hop le." -ForegroundColor Yellow
    $br.Close(); $fs.Close(); exit
}

# ================================================================
# RESOURCE DATA TABLE (sau header):
#   per entry (20 bytes):
#   [8]  resource_hash   uint64
#   [8]  data_offset     uint64
#   [4]  data_size_flags uint32  (bit 31 = XOR scramble flag)
# ================================================================

Write-Host ("Doc resource data table ({0:N0} entries)..." -f $resCount) -ForegroundColor Cyan

# Skip patch deletion entries nếu có (mỗi entry 8 bytes)
# patchDelCnt > 0 chỉ trong patch file, chunk0/1 thường = 0
if ($patchDelCnt -gt 0 -and $patchDelCnt -lt 100000) {
    Write-Host ("Skip {0} patch deletion entries..." -f $patchDelCnt) -ForegroundColor Gray
    $br.ReadBytes($patchDelCnt * 8) | Out-Null
}

$dataEntries = @()
$maxRead = [Math]::Min($resCount, 500000)

for ($i = 0; $i -lt $maxRead; $i++) {
    $hash      = $br.ReadUInt64()   # 8 bytes
    $offset    = $br.ReadUInt64()   # 8 bytes
    $sizeFlags = $br.ReadUInt32()   # 4 bytes
    $dataEntries += [PSCustomObject]@{
        Hash      = $hash
        Offset    = $offset
        SizeFlags = $sizeFlags
    }
}

Write-Host ("Doc duoc {0:N0} entries tu data table." -f $dataEntries.Count)
Write-Host ""

# ================================================================
# RESOURCE METADATA TABLE (sau data table):
#   per entry:
#   [4]  type_extension   char[4]  (e.g. "LOCR", "TEMP", "TEXT"...)
#   [4]  ref_table_size   uint32
#   [4]  states_table_sz  uint32
#   [4]  size_final       uint32
#   [4]  size_inmem       uint32
#   [4]  size_invmem      uint32
#   then if ref_table_size > 0:
#     [4] ref_count uint32
#     [1*ref_count] flags
#     [8*ref_count] ref hashes
# ================================================================

Write-Host "Doc resource metadata table (type extensions)..." -ForegroundColor Cyan

$typeCounter = @{}
$typeSamples = @{}
$maxSamples  = 3

for ($i = 0; $i -lt $dataEntries.Count; $i++) {
    $typeBytes = $br.ReadBytes(4)
    $refSz     = $br.ReadUInt32()
    $stateSz   = $br.ReadUInt32()
    $sizeFinal = $br.ReadUInt32()
    $sizeInMem = $br.ReadUInt32()
    $sizeVMem  = $br.ReadUInt32()

    try {
        $typeStr = [System.Text.Encoding]::ASCII.GetString($typeBytes)
        $isPrint = $true
        foreach ($c in $typeBytes) {
            if ($c -lt 0x20 -or $c -gt 0x7E) { $isPrint = $false; break }
        }
        if (-not $isPrint) { $typeStr = "[binary]" }
    } catch { $typeStr = "[binary]" }

    # Count type
    if ($typeCounter.ContainsKey($typeStr)) {
        $typeCounter[$typeStr]++
    } else {
        $typeCounter[$typeStr] = 1
        $typeSamples[$typeStr] = @()
    }
    if ($typeSamples[$typeStr].Count -lt $maxSamples) {
        $typeSamples[$typeStr] += ("0x{0:X16}" -f $dataEntries[$i].Hash)
    }

    # Skip references nếu có
    if ($refSz -gt 0 -and $refSz -lt 1000000) {
        $br.ReadBytes($refSz) | Out-Null
    }
}

Write-Host ("Done. {0} resource types phat hien." -f $typeCounter.Count)
Write-Host ""

# ================================================================
# KET QUA
# ================================================================
$sep = "=" * 70
Write-Host $sep
Write-Host ("{0,-15} {1,10}  {2}" -f "Resource Type", "Count", "Sample hashes")
Write-Host $sep

$sorted = $typeCounter.GetEnumerator() | Sort-Object Value -Descending
foreach ($entry in $sorted | Select-Object -First 50) {
    $t = $entry.Key
    $cnt = $entry.Value
    $samples = if ($typeSamples[$t]) { "  " + ($typeSamples[$t] -join ", ") } else { "" }
    Write-Host ("{0,-15} {1,10}{2}" -f $t, $cnt, $samples)
}

Write-Host $sep
Write-Host ""

# --- Tim LOCR va type lien quan ---
$locrCount = if ($typeCounter.ContainsKey("LOCR")) { $typeCounter["LOCR"] } else { 0 }
if ($locrCount -gt 0) {
    Write-Host "[OK] Tim thay $locrCount file LOCR!" -ForegroundColor Green
    Write-Host ("     Samples: {0}" -f ($typeSamples["LOCR"] -join ", "))
} else {
    Write-Host "[!] Khong co LOCR." -ForegroundColor Yellow
    $relatedTypes = $typeCounter.Keys | Where-Object {
        $_ -match "LOC|TEXT|LANG|STR|DLGE|CLNG|LINE|SUBT|DIAL|SCEN|CONV"
    }
    if ($relatedTypes) {
        Write-Host "[i] Type co the lien quan den text/localization:" -ForegroundColor Cyan
        foreach ($t in $relatedTypes) {
            Write-Host ("    {0,-15} {1,8} entries  samples: {2}" -f $t, $typeCounter[$t], ($typeSamples[$t] -join ", "))
        }
    } else {
        Write-Host "[i] Khong thay type nao lien quan." -ForegroundColor Gray
        Write-Host "[i] Tat ca types co trong file:" -ForegroundColor Gray
        $typeCounter.Keys | Sort-Object | ForEach-Object { Write-Host "    $_" }
    }
}

$br.Close()
$fs.Close()
Write-Host ""
