-- Log the sprite entries used by Time Twist's static prompt.
-- Read-only probe: no file or operating-system access.

local frame = 0

local function dumpPromptSprites()
    emu.log("PROMPT_SPRITES_BEGIN")
    for sprite = 0, 63 do
        local offset = sprite * 4
        local y = emu.read(offset, emu.memType.nesSpriteRam, false)
        local tile = emu.read(offset + 1, emu.memType.nesSpriteRam, false)
        local attributes = emu.read(offset + 2, emu.memType.nesSpriteRam, false)
        local x = emu.read(offset + 3, emu.memType.nesSpriteRam, false)
        if y >= 130 and y <= 190 then
            emu.log(string.format(
                "S%02d Y=%02X TILE=%02X ATTR=%02X X=%02X",
                sprite, y, tile, attributes, x
            ))
        end
    end
    emu.log("PROMPT_SPRITES_END")
end

emu.addEventCallback(function()
    frame = frame + 1
    if frame == 2 then
        dumpPromptSprites()
    end
end, emu.eventType.endFrame)
