-- Log only likely text tiles from the active NES nametable.
-- This keeps the read-only probe compact enough to inspect in Mesen's log pane.

local frame = 0

local function dumpUiTiles()
    emu.log("UI_TILES_BEGIN")
    for row = 0, 29 do
        local values = {}
        for column = 0, 31 do
            local address = 0x2000 + row * 32 + column
            local value = emu.read(address, emu.memType.nesPpuDebug, false)
            if value >= 0xB0 then
                values[#values + 1] = string.format("%02d=%02X", column, value)
            end
        end
        if #values > 0 then
            emu.log(string.format("R%02d %s", row, table.concat(values, " ")))
        end
    end
    emu.log("UI_TILES_END")
end

emu.addEventCallback(function()
    frame = frame + 1
    if frame == 2 then
        dumpUiTiles()
    end
end, emu.eventType.endFrame)
