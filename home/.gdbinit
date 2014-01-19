define wchar_print
        echo "

        set $i = 0
        while (1 == 1)
                set $c = (char)(($arg0)[$i++])
                if ($c == '\0')
                        loop_break
                end
                printf "%c", $c
        end

        echo "\n
end

# Print a C++ string.
define ps
  print $arg0.c_str()
end

# Print a C++ wstring or wchar_t*.
define pws
  printf "\""
  set $c = (wchar_t*)$arg0
  while ( *$c )
    if ( *$c > 0x7f )
      printf "[%x]", *$c
    else
      printf "%c", *$c
    end
    set $c++
  end
  printf "\"\n"
end

# Print a FilePath.
define pfp
  print $arg0.value().c_str()
end

document wchar_print
wchar_print <wstr>
Print ASCII part of <wstr>, which is a wide character string of type wchar_t*.
end

define string_print
	wchar_print ($arg0)
end

document string_print
	string_print <String>
	Print the ASCII representation of the WTF::String object.
end

define kurl_print
#	string_print ($arg0).urlString
	string_print ($arg0).m_string
end

document kurl_print
	kurl_print <KURL>
	Print the ASCII representation of the WebCore::KURL object.
end

define request_print
	kurl_print ($arg0).url()
end

document request_print
	request_print <ResourceRequest>
	Print the ASCII representation of the ResourceRequest object.
end

define flrequest_print
	request_print ($arg0).resourceRequest()
end

document flrequest_print
	flrequest_print <FrameLoadRequest>
	Print the ASCII representation of the FrameLoadRequest object.
end

define jsbt
	p v8::V8::PrintStack()
end

document jsbt
	jsbt
	Print the JavaScript stack for the current context
end

handle SIGPIPE nostop noprint pass

# May not always be what I want, but the only process I debug that is forked 
# is LunaSysMgr and in that case I only care about the WebKit process.
#set follow-fork-mode child

set print pretty on

source .gdbinit_stl

define infothreads
  set logging off
  set logging file /tmp/tmp_file_gdb_names
  set pagination off
  set logging overwrite on
  set logging redirect on
  set logging on
  info threads
  set logging off
  set logging redirect off
  set logging overwrite off
  set pagination on
  shell /home/mumfordc/bin/gdb_bt_to_name.rb /tmp/tmp_file_gdb_names
  shell rm -f /tmp/tmp_file_gdb_names
end

define threadbt
  set logging off
  set logging file /tmp/tmp_file_gdb_names
  set pagination off
  set logging overwrite on
  set logging redirect on
  set logging on
  thread apply all bt
  set logging off
  set logging redirect off
  set logging overwrite off
  set pagination on
  shell /home/mumfordc/bin/gdb_bt_to_name.rb /tmp/tmp_file_gdb_names
  shell rm -f /tmp/tmp_file_gdb_names
end
