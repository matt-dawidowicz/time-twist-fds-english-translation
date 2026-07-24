-- Log the three nametable rows containing Time Twist's static prompt.
-- Read-only probe: no file or operating-system access.

local frame = 0

local function dumpPromptRows()
    emu.log("PROMPT_ROWS_BEGIN")
    for row = 17, 19 do
        local values = {}
        for column = 0, 31 do
            local address = 0x2000 + row * 32 + column
            values[#values + 1] = string.format(
                "%02X",
                emu.read(address, emu.memType.nesPpuDebug, false)
            )
        end
        emu.log(string.format("R%02d %s", row, table.concat(values, " ")))
    end
    emu.log("PROMPT_ROWS_END")
end

emu.addEventCallback(function()
    frame = frame + 1
    if frame == 2 then
        dumpPromptRows()
    end
end, emu.eventType.endFrame)
