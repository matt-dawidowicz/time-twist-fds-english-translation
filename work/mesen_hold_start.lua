-- Hold Start long enough for a frame-polled NES game to see it.
-- This script uses only Mesen's controller API; it does not access files or OS APIs.
local polls = 0

emu.addEventCallback(function()
	polls = polls + 1
	emu.setInput({ start = polls <= 90 }, 0)
end, emu.eventType.inputPolled)
