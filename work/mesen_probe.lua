-- Headless MesenCE probe used while reverse-engineering Time Twist.
-- It periodically presses Start/A, then captures the screen, CHR RAM, and
-- CPU RAM so the font/text decoder can be checked against actual execution.

local outputRoot = os.getenv("TIME_TWIST_CAPTURE_DIR") or "work/mesen_capture"
local frame = 0

local function writeBinary(path, data)
    local file = assert(io.open(path, "wb"))
    file:write(data)
    file:close()
end

local function dumpMemory(path, memoryType, size)
    local values = {}
    for address = 0, size - 1 do
        values[#values + 1] = string.char(emu.read(address, memoryType, false))
    end
    writeBinary(path, table.concat(values))
end

local function applyInput()
    local pulse = frame % 120
    emu.setInput({ start = pulse == 30, a = pulse == 60 }, 0)
end

local function finishProbe()
    writeBinary(outputRoot .. "/screen.png", emu.takeScreenshot())
    dumpMemory(outputRoot .. "/chr.bin", emu.memType.nesChrRam, 0x2000)
    dumpMemory(outputRoot .. "/cpu.bin", emu.memType.nesDebug, 0x10000)
    emu.stop(0)
end

local function endFrame()
    frame = frame + 1
    if frame >= 1200 then
        finishProbe()
    end
end

emu.addEventCallback(applyInput, emu.eventType.inputPolled)
emu.addEventCallback(endFrame, emu.eventType.endFrame)
