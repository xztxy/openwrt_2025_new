# File name: immortalwrt_x86.sh
# Description: OpenWrt DIY script part 2 (After Update feeds)
#
# Modify default IP
sed -i 's/192.168.1.1/192.168.100.252/g' package/base-files/files/bin/config_generate
#
##### 移除要替换的包
# 删除老argon
rm -rf feeds/luci/themes/luci-theme-argon
rm -rf feeds/luci/applications/luci-app-argon-config
# 删除英文版netdata
rm -rf feeds/luci/applications/luci-app-netdata
##### Git稀疏克隆
# 参数1是分支名, 参数2是仓库地址, 参数3是子目录，同一个仓库下载多个文件夹直接在后面跟文件名或路径，空格分开
function git_sparse_clone() {
  branch="$1" repourl="$2" && shift 2
  git clone --depth=1 -b $branch --single-branch --filter=blob:none --sparse $repourl
  repodir=$(echo $repourl | awk -F '/' '{print $(NF)}')
  cd $repodir && git sparse-checkout set $@
  mv -f $@ ../package
  cd .. && rm -rf $repodir
}

##### Themes
# 拉取argon主题
git clone --depth=1 -b master https://github.com/jerrykuku/luci-theme-argon package/luci-theme-argon
git clone --depth=1 -b master https://github.com/jerrykuku/luci-app-argon-config package/luci-app-argon-config

##### 添加额外插件
# 拉取中文版netdata
git clone --depth=1 -b master https://github.com/sirpdboy/luci-app-netdata package/luci-app-netdata
# 添加Lucky
git clone --depth=1 -b main https://github.com/sirpdboy/luci-app-lucky.git package/lucky
# 添加系统高级设置加强版
git clone --depth=1 -b main https://github.com/sirpdboy/luci-app-advancedplus package/luci-app-advancedplus
# 拉取定时设置
git clone --depth=1 https://github.com/sirpdboy/luci-app-autotimeset package/luci-app-autotimeset
# eqosplus定时限速
git clone --depth=1 https://github.com/sirpdboy/luci-app-eqosplus package/luci-app-eqosplus
# 家长控制
git clone --depth=1 -b main https://github.com/sirpdboy/luci-app-parentcontrol package/luci-app-parentcontrol
# 设备关机功能
git clone --depth=1 https://github.com/sirpdboy/luci-app-poweroffdevice package/luci-app-poweroffdevice
# 添加adguardhome,bypass,timecontrol,control-timewol，管控过滤,访问限制
git_sparse_clone main https://github.com/kenzok8/small-package luci-app-adguardhome luci-app-bypass luci-app-control-weburl luci-app-control-webrestriction
# 添加istore
git_sparse_clone main https://github.com/linkease/istore-ui app-store-ui
git_sparse_clone main https://github.com/linkease/istore luci
# 添加ssrplus
git clone --depth=1 -b master https://github.com/fw876/helloworld package/luci-app-ssr-plus
