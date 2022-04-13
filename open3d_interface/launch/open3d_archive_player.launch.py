import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    ld = LaunchDescription()

    config = os.path.join(
        get_package_share_directory('open3d_interface'),
        'config',
        'archive_publisher_astra_params.yaml'
    )

    print(config)

    node = Node(
        package='open3d_interface',
        executable='open3d_archive_player',
        name='open3d_archive_player',
        output='screen',
        emulate_tty=True,
        parameters=[config]
    )

    ld.add_action(node)

    return ld
