function Div(elem)
  if elem.classes:includes("cell") then
    local blocks = elem.content
    local code_block = nil
    local output_block_index = nil
    local output_text = nil

    for i, block in ipairs(blocks) do
      if block.t == "CodeBlock" and block.classes:includes("python") then
        code_block = block
      elseif block.t == "Div" and block.classes:includes("cell-output-stdout") then
        for _, subblock in ipairs(block.content) do
          if subblock.t == "CodeBlock" then
            output_text = subblock.text
            output_block_index = i
          end
        end
      end
    end

    if code_block and output_text then
      local code_lines = {}
      for line in code_block.text:gmatch("([^\r\n]*)\r?\n?") do
        table.insert(code_lines, line)
      end

      -- Add a blank line before output comments
      table.insert(code_lines, "")

      -- Add each output line as a comment
      for line in output_text:gmatch("([^\r\n]*)\r?\n?") do
        table.insert(code_lines, "# " .. line)
      end

      code_block.text = table.concat(code_lines, "\n")

      -- Remove the original output block
      if output_block_index then
        table.remove(blocks, output_block_index)
      end
    end
  end
  return elem
end
