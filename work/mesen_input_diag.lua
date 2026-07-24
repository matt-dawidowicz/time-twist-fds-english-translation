-- Diagnose Player 1 input without file or operating-system access.
-- The pulse starts after a short release period so edge-triggered games see it.
local polls = 0

local function dump(label)
  local input = emu.getInput(0)
  emu.log(label)
  for key, value in pairs(input) do
    emu.log("  " .. key .. "=" .. tostring(value))
  end
end

emu.addEventCallback(function()
  polls = polls + 1
  local pressed = polls > 30 and polls <= 90
  emu.setInput({ a = pressed }, 0)

  if polls == 1 then
    dump("Player 1 controller fields before pulse")
  elseif polls == 45 then
    dump("Player 1 controller fields during A pulse")
  elseif polls == 105 then
    dump("Player 1 controller fields after pulse")
  end
end, emu.eventType.inputPolled)
