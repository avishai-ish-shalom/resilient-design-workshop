local math = require "math"
local io = require "io"

ids = {
}

images = {
    "small.png",
    "medium.png",
    "large.png",
    "larger.png",
}

extra_args = nil

function read_file(filename)
    local file = io.open(filename, "rb")
    local file_body = file:read("*a")
    file:close()
    return file_body
end

function init(args)
    if args[1] then
        local f = io.open(args[1])
        for line in f:lines() do
            table.insert(ids, line)
        end
        f:close()
    end

    if args[2] then
        extra_args = args[2]
    end
end


function request()
    if math.random(100) < 10 then
        return wrk.format('PUT', '/image/', {['Content-Type'] = 'image/png'}, read_file('small.png'))
    else
        local id = ids[math.random(1, #ids)]
        local path = '/image/' .. id
        if extra_args then
            path = path .. '?' .. extra_args
        end
        return wrk.format('GET', path)
    end
end