local function stopOnFrame()
    emu.stop(7)
end

emu.addEventCallback(stopOnFrame, emu.eventType.startFrame)
