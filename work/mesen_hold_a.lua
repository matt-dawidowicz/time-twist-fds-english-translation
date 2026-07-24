-- Hold the NES A button long enough for a frame-polled game to see it.
-- This script uses only Mesen's controller API; it does not access files or OS APIs.
local polls = 0

emu.addEventCallback(function()
	polls = polls + 1
  emu.setInput({ a = polls <= 300 }, 0)
end, emu.eventType.inputPolled)
