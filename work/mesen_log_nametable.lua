-- Log the active NES nametable as tile IDs without using file or OS access.
-- This is a read-only reverse-engineering probe for Time Twist's static UI.

local frame = 0

local function dumpNametable()
    emu.log("NAMETABLE_BEGIN")
    for row = 0, 29 do
        local values = {}
        for column = 0, 31 do
            local address = 0x2000 + row * 32 + column
            values[#values + 1] = string.format("%02X", emu.read(address, emu.memType.nesPpuDebug, false))
        end
        emu.log(string.format("NT%02d %s", row, table.concat(values, " ")))
    end
    emu.log("NAMETABLE_END")
end

emu.addEventCallback(function()
    frame = frame + 1
    if frame == 2 then
        dumpNametable()
    end
end, emu.eventType.endFrame)
