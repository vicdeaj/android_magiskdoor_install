# need boot.img to flash
# need lk.img to flash
# mtkclient in ../mtkclient

mtkclient="../mtkclient/mtk"
./$mtkclient w boot boot.img
./$mtkclient w lk lk.img
./$mtkclient w lk2 lk.img
./$mtkclient da seccfg unlock


