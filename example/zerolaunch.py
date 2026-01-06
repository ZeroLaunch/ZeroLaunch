import zerolaunch

zerolaunch = new zerolaunch()

structure_post = new structure()
structure_post.add_field("id")
structure_post.add_field("title")
structure_post.add_field("description")
structure_post.add_field("create_at")

zerolaunch.add_structures(structure_post)
zerolaunch.port = 3000
