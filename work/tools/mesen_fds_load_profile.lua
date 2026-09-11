-- Time Twist FDS LoadFiles profiler for Mesen 2.
-- Read-only instrumentation: no memory is modified.
--
-- Logs every known NOV2 wrapper invocation around BIOS LoadFiles ($E1F8),
-- including the runtime-patched DiskID/file list and elapsed frames/cycles.

local MEM = emu.memType.nesDebug
local LOAD_FILES = 0xE1F8
local PRIMARY_CALL = 0x6008
local PRIMARY_RETURN = 0x600F
local SECONDARY_CALL = 0x606D
local SECONDARY_RETURN = 0x6074
local MAX_FILE_IDS = 20

local sequence = 0
local frame = 0
local active = nil

local function read8(address)
    return emu.read(address, MEM, false)
end

local function read16(address)
    return read8(address) | (read8(address + 1) << 8)
end

local function hex8(value)
    return string.format("%02X", value)
end

local function ascii4(address)
    local chars = {}
    for i = 0, 3 do
        local value = read8(address + i)
        if value >= 0x20 and value <= 0x7E then
            chars[#chars + 1] = string.char(value)
        else
            chars[#chars + 1] = "."
        end
    end
    return table.concat(chars)
end

local function readFileIds(address)
    local values = {}
    for i = 0, MAX_FILE_IDS - 1 do
        local value = read8(address + i)
        if value == 0xFF then
            break
        end
        values[#values + 1] = hex8(value)
    end
    if #values == 0 then
        return "FF"
    end
    return table.concat(values, ",")
end

local function currentCycle()
    local state = emu.getState()
    return state["cpu.cycleCount"] or 0
end

local function beginLoad(kind, callAddress)
    sequence = sequence + 1
    local diskPtr = read16(callAddress + 3)
    local listPtr = read16(callAddress + 5)
    local diskGame = ascii4(diskPtr + 1)
    local diskSide = read8(diskPtr + 6)
    local diskNumber = read8(diskPtr + 7)
    local ids = readFileIds(listPtr)
    active = {
        seq = sequence,
        kind = kind,
        callAddress = callAddress,
        frame = frame,
        cycle = currentCycle(),
        diskPtr = diskPtr,
        listPtr = listPtr,
        diskGame = diskGame,
        diskSide = diskSide,
        diskNumber = diskNumber,
        ids = ids,
    }
    emu.log(string.format(
        "TTLOAD\tSTART\tseq=%d\tframe=%d\tcycle=%d\tkind=%s\tcall=$%04X\tgame=%s\tside=%d\tdisk=%d\tdisk_ptr=$%04X\tlist_ptr=$%04X\tids=%s",
        active.seq,
        active.frame,
        active.cycle,
        active.kind,
        active.callAddress,
        active.diskGame,
        active.diskSide,
        active.diskNumber,
        active.diskPtr,
        active.listPtr,
        active.ids
    ))
end

local function endLoad(expectedKind)
    if active == nil then
        emu.log(string.format(
            "TTLOAD\tRETURN_WITHOUT_START\tframe=%d\tkind=%s",
            frame,
            expectedKind
        ))
        return
    end
    local state = emu.getState()
    local finishCycle = state["cpu.cycleCount"] or 0
    local errorCode = state["cpu.a"] or 0
    local loadedCount = state["cpu.y"] or 0
    emu.log(string.format(
        "TTLOAD\tEND\tseq=%d\tframe=%d\tcycle=%d\tframes=%d\tcycles=%d\tkind=%s\terror=$%02X\tloaded=%d\tgame=%s\tside=%d\tdisk=%d\tids=%s",
        active.seq,
        frame,
        finishCycle,
        frame - active.frame,
        finishCycle - active.cycle,
        active.kind,
        errorCode,
        loadedCount,
        active.diskGame,
        active.diskSide,
        active.diskNumber,
        active.ids
    ))
    active = nil
end

emu.addEventCallback(function()
    frame = frame + 1
end, emu.eventType.endFrame)

emu.addMemoryCallback(function()
    beginLoad("scenario", PRIMARY_CALL)
end, emu.callbackType.exec, PRIMARY_CALL)

emu.addMemoryCallback(function()
    endLoad("scenario")
end, emu.callbackType.exec, PRIMARY_RETURN)

emu.addMemoryCallback(function()
    beginLoad("nov4_save", SECONDARY_CALL)
end, emu.callbackType.exec, SECONDARY_CALL)

emu.addMemoryCallback(function()
    endLoad("nov4_save")
end, emu.callbackType.exec, SECONDARY_RETURN)

emu.addMemoryCallback(function()
    if active == nil then
        local state = emu.getState()
        emu.log(string.format(
            "TTLOAD\tUNEXPECTED_BIOS_ENTRY\tframe=%d\tcycle=%d\tpc=$%04X",
            frame,
            state["cpu.cycleCount"] or 0,
            LOAD_FILES
        ))
    end
end, emu.callbackType.exec, LOAD_FILES)

local info = emu.getRomInfo()
local sha1 = "unknown"
if info ~= nil and info.fileSha1Hash ~= nil then
    sha1 = info.fileSha1Hash
end
emu.log("TTLOAD\tREADY\trom_sha1=" .. sha1)
emu.displayMessage("Time Twist load profiler", "LoadFiles tracing enabled")
